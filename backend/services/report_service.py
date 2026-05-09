"""
VEXX AI — PDF Report Service
Gera relatórios executivos em PDF com ReportLab Platypus.
Salva em backend/database/reports/ e devolve o caminho.
"""

import os
from datetime import datetime, date, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend

from database.models import User
from services.dashboard_service import get_dashboard_stats
from services.finance_service import get_financial_summary
from services.analytics_service import (
    get_analytics_overview, get_revenue_trend, get_top_categories,
)
from services.crm_service import get_pipeline_summary


# ── Brand colors ────────────────────────────────────────────────────────────
BRAND_PURPLE = colors.HexColor('#6d28d9')
BRAND_DARK   = colors.HexColor('#0c0c18')
BRAND_GREEN  = colors.HexColor('#10b981')
BRAND_RED    = colors.HexColor('#f43f5e')
BRAND_BLUE   = colors.HexColor('#3b82f6')
BRAND_AMBER  = colors.HexColor('#f59e0b')
TEXT_MUTED   = colors.HexColor('#818da6')
SURFACE      = colors.HexColor('#f5f7fb')
BORDER       = colors.HexColor('#e2e8f0')


def _format_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')


def _styles():
    base = getSampleStyleSheet()
    return {
        'h1': ParagraphStyle('h1', parent=base['Heading1'], fontSize=22,
                             textColor=BRAND_DARK, leading=26, spaceAfter=4),
        'h2': ParagraphStyle('h2', parent=base['Heading2'], fontSize=14,
                             textColor=BRAND_PURPLE, leading=18, spaceBefore=10, spaceAfter=8),
        'h3': ParagraphStyle('h3', parent=base['Heading3'], fontSize=11,
                             textColor=BRAND_DARK, leading=14, spaceAfter=4),
        'p':  ParagraphStyle('p',  parent=base['Normal'], fontSize=9,
                             textColor=BRAND_DARK, leading=13),
        'muted': ParagraphStyle('muted', parent=base['Normal'], fontSize=8.5,
                                textColor=TEXT_MUTED, leading=12),
        'small_right': ParagraphStyle('sr', parent=base['Normal'], fontSize=8,
                                      textColor=TEXT_MUTED, alignment=TA_RIGHT),
        'kpi_label': ParagraphStyle('kl', parent=base['Normal'], fontSize=8,
                                    textColor=TEXT_MUTED, alignment=TA_CENTER),
        'kpi_val':   ParagraphStyle('kv', parent=base['Normal'], fontSize=16,
                                    textColor=BRAND_DARK, alignment=TA_CENTER, leading=18),
    }


# ── Page header/footer ──────────────────────────────────────────────────────
def _draw_chrome(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(BRAND_PURPLE)
    canvas.rect(0, A4[1] - 20*mm, A4[0], 20*mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 14)
    canvas.drawString(15*mm, A4[1] - 13*mm, 'VEXX AI')
    canvas.setFont('Helvetica', 9)
    canvas.drawString(38*mm, A4[1] - 13*mm, '· Business Suite — Relatório Executivo')
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(A4[0] - 15*mm, A4[1] - 13*mm,
                           datetime.now().strftime('%d/%m/%Y %H:%M'))

    # Footer
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(15*mm, 10*mm, 'Confidencial · Gerado automaticamente pela VEXX AI')
    canvas.drawRightString(A4[0] - 15*mm, 10*mm, f'Página {doc.page}')
    canvas.restoreState()


# ── Components ──────────────────────────────────────────────────────────────
def _kpi_grid(stats, fin, styles):
    """4 KPI cards in a row."""
    cells = [
        ('Receita do mês',  _format_brl(fin.get('month_income', 0)),  BRAND_GREEN),
        ('Despesas do mês', _format_brl(fin.get('month_expenses', 0)), BRAND_RED),
        ('Lucro do mês',    _format_brl(fin.get('month_profit', 0)),  BRAND_BLUE),
        ('Faturas pendentes', f"{fin.get('pending_invoices', 0)} · " +
                              _format_brl(fin.get('pending_amount', 0)), BRAND_AMBER),
    ]

    rows = [[
        Paragraph(f'<font color="{c.hexval()}">{title}</font>', styles['kpi_label'])
        for title, _, c in cells
    ], [
        Paragraph(value, styles['kpi_val']) for _, value, _ in cells
    ]]
    t = Table(rows, colWidths=[4.4*cm]*4)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SURFACE),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def _revenue_chart(trend):
    """Bar chart receita vs despesas — últimos 30 dias agrupados em 6 buckets."""
    if not trend:
        return Spacer(1, 0)

    # Bucket em ~6 colunas
    n = len(trend)
    bucket = max(1, n // 6)
    grouped = []
    for i in range(0, n, bucket):
        chunk = trend[i:i + bucket]
        grouped.append({
            'label':    chunk[-1]['date'] if chunk else '',
            'income':   sum(c['income']   for c in chunk),
            'expenses': sum(c['expenses'] for c in chunk),
        })

    drawing = Drawing(450, 180)
    chart = VerticalBarChart()
    chart.x = 50; chart.y = 30
    chart.width  = 380
    chart.height = 130
    chart.data = [
        [g['income']   for g in grouped],
        [g['expenses'] for g in grouped],
    ]
    chart.categoryAxis.categoryNames = [g['label'] for g in grouped]
    chart.bars[0].fillColor = BRAND_GREEN
    chart.bars[1].fillColor = BRAND_RED
    chart.bars.strokeWidth = 0
    chart.barWidth = 8
    chart.groupSpacing = 10
    chart.valueAxis.gridStrokeColor = BORDER
    chart.valueAxis.gridStrokeWidth = 0.3
    chart.valueAxis.visibleGrid = True
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = TEXT_MUTED
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = TEXT_MUTED

    drawing.add(chart)
    return drawing


def _pipeline_table(pipeline, styles):
    rows = [['Estágio', 'Quantidade', 'Valor total']]
    stage_label = {
        'prospect': 'Prospecção', 'qualified': 'Qualificado', 'proposal': 'Proposta',
        'negotiation': 'Negociação', 'closed_won': 'Ganho', 'closed_lost': 'Perdido',
    }
    for s in pipeline or []:
        rows.append([
            stage_label.get(s['stage'], s['stage']),
            str(s.get('count', 0)),
            _format_brl(s.get('total_value', 0)),
        ])

    t = Table(rows, colWidths=[6*cm, 4*cm, 5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_DARK),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('GRID',       (0, 0), (-1, -1), 0.3, BORDER),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',      (1, 1), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, SURFACE]),
    ]))
    return t


def _categories_table(cats, styles):
    if not cats:
        return Paragraph('<i>Sem categorias com receita registradas.</i>', styles['muted'])
    rows = [['Categoria', 'Receita total']]
    for c in cats:
        rows.append([c.get('category') or 'Sem categoria', _format_brl(c.get('total', 0))])

    t = Table(rows, colWidths=[10*cm, 5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_PURPLE),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('GRID',       (0, 0), (-1, -1), 0.3, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('TEXTCOLOR', (1, 1), (-1, -1), BRAND_GREEN),
    ]))
    return t


# ── Main API ────────────────────────────────────────────────────────────────
def generate_executive_pdf(user_id: int) -> tuple[str, str]:
    """
    Gera PDF executivo em backend/database/reports/<user>_<timestamp>.pdf
    Retorna (filepath, filename).
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError('Usuário não encontrado.')

    # Coleta de dados
    stats     = get_dashboard_stats(user_id)
    fin       = get_financial_summary(user_id)
    overview  = get_analytics_overview(user_id)
    trend     = get_revenue_trend(user_id, 30)
    cats      = get_top_categories(user_id)
    pipeline  = get_pipeline_summary(user_id)

    styles = _styles()

    # Setup arquivo
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'database', 'reports',
    )
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'executivo_{user_id}_{timestamp}.pdf'
    filepath = os.path.join(reports_dir, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=27*mm, bottomMargin=18*mm,
    )

    story = []

    # ── Capa ─────────────────────────────────────────
    story.append(Paragraph('Relatório Executivo Mensal', styles['h1']))
    company = user.company or '—'
    story.append(Paragraph(
        f'<b>{user.first_name} {user.last_name}</b> · {company} · '
        f'<font color="{TEXT_MUTED.hexval()}">Plano {user.plan.title()}</font>',
        styles['p']))
    today = date.today()
    period_start = today.replace(day=1)
    story.append(Paragraph(
        f'Período: {period_start.strftime("%d/%m/%Y")} – {today.strftime("%d/%m/%Y")}',
        styles['muted']))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', color=BORDER, thickness=0.5))
    story.append(Spacer(1, 14))

    # ── KPIs ─────────────────────────────────────────
    story.append(Paragraph('Indicadores principais', styles['h2']))
    story.append(_kpi_grid(stats, fin, styles))
    story.append(Spacer(1, 14))

    # ── Receita vs Despesas ──────────────────────────
    story.append(Paragraph('Receita vs Despesas — últimos 30 dias', styles['h2']))
    story.append(_revenue_chart(trend))
    story.append(Spacer(1, 12))

    # ── Insights ─────────────────────────────────────
    story.append(Paragraph('Insights & métricas', styles['h2']))
    bullet_rows = [
        ['Novos contatos (30d)',     str(overview.get('contacts_30d', 0))],
        ['Crescimento de contatos',  f"{overview.get('contacts_growth', 0)}%"],
        ['Receita (30d)',            _format_brl(overview.get('revenue_30d', 0))],
        ['Crescimento de receita',   f"{overview.get('revenue_growth', 0)}%"],
        ['Taxa de conversão',        f"{overview.get('conversion_rate', 0)}%"],
        ['Leads ganhos',             str(overview.get('leads_won', 0))],
        ['Leads perdidos',           str(overview.get('leads_lost', 0))],
        ['Saldo acumulado',          _format_brl(fin.get('balance', 0))],
    ]
    t = Table(bullet_rows, colWidths=[8*cm, 7*cm])
    t.setStyle(TableStyle([
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('TEXTCOLOR',  (0, 0), (0, -1), TEXT_MUTED),
        ('TEXTCOLOR',  (1, 0), (1, -1), BRAND_DARK),
        ('FONTNAME',   (1, 0), (1, -1), 'Helvetica-Bold'),
        ('ALIGN',      (1, 0), (1, -1), 'RIGHT'),
        ('LINEBELOW',  (0, 0), (-1, -2), 0.3, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # ── Pipeline ─────────────────────────────────────
    story.append(Paragraph('Pipeline de vendas', styles['h2']))
    story.append(_pipeline_table(pipeline, styles))
    story.append(Spacer(1, 14))

    # ── Categorias ───────────────────────────────────
    story.append(Paragraph('Top categorias de receita', styles['h2']))
    story.append(_categories_table(cats, styles))
    story.append(Spacer(1, 18))

    # ── Recomendação IA (rodapé) ─────────────────────
    story.append(HRFlowable(width='100%', color=BORDER, thickness=0.5))
    story.append(Spacer(1, 8))

    profit_margin = 0
    if fin.get('month_income', 0) > 0:
        profit_margin = (fin['month_profit'] / fin['month_income']) * 100

    rec = []
    if profit_margin > 50:
        rec.append('• Margem de lucro saudável — considere reinvestir em crescimento.')
    elif profit_margin < 20:
        rec.append('• Margem apertada — revisar custos e renegociar contratos.')
    if overview.get('conversion_rate', 0) < 20:
        rec.append('• Taxa de conversão baixa — investir em qualificação e follow-up de leads.')
    if fin.get('pending_invoices', 0) >= 3:
        rec.append(f'• {fin["pending_invoices"]} faturas pendentes — acionar cobrança automática.')
    if not rec:
        rec.append('• Operação saudável — mantenha consistência e considere expansão.')

    story.append(Paragraph('Recomendações estratégicas', styles['h3']))
    for r in rec:
        story.append(Paragraph(r, styles['muted']))

    doc.build(story, onFirstPage=_draw_chrome, onLaterPages=_draw_chrome)

    return filepath, filename


def list_user_reports(user_id: int) -> list:
    """Lista PDFs do usuário no diretório."""
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'database', 'reports',
    )
    if not os.path.isdir(reports_dir):
        return []

    prefix = f'executivo_{user_id}_'
    items = []
    for fn in sorted(os.listdir(reports_dir), reverse=True):
        if fn.startswith(prefix) and fn.endswith('.pdf'):
            full = os.path.join(reports_dir, fn)
            try:
                ts = datetime.strptime(fn.replace(prefix, '').replace('.pdf', ''),
                                       '%Y%m%d_%H%M%S')
            except ValueError:
                ts = datetime.fromtimestamp(os.path.getmtime(full))
            items.append({
                'filename': fn,
                'created_at': ts.isoformat(),
                'size_kb': round(os.path.getsize(full) / 1024, 1),
            })
    return items[:50]
