/* ══════════════════════════════════════════════════════════
   VEXX AI — AI Assistant page (chat + gerenciamento de conversas)
   Event delegation, sem inline handlers — mais confiável.
══════════════════════════════════════════════════════════ */

let _conversationId = null;
let _conversations  = [];
let _messages       = [];
let _renameTargetId = null;
let _deleteTargetId = null;

document.addEventListener('DOMContentLoaded', () => {
  loadConversations();
  autoResizeInput();

  /* Pré-preencher pergunta da query string ?q=... */
  const params = new URLSearchParams(window.location.search);
  const initial = params.get('q');
  if (initial) {
    document.getElementById('chat-input').value = initial;
    setTimeout(sendMessage, 200);
  }

  /* Event delegation: trata todos os cliques na sidebar de conversas */
  const history = document.getElementById('chat-history');
  if (history) history.addEventListener('click', onHistoryClick);

  /* Fechar dropdowns ao clicar fora */
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.conv-dropdown') && !e.target.closest('.conv-menu-btn')) {
      closeAllDropdowns();
    }
  });

  /* Bind do form de rename */
  const renameForm = document.getElementById('rename-form');
  if (renameForm) renameForm.addEventListener('submit', confirmRename);

  /* Bind do botão de delete (no modal) */
  const delBtn = document.getElementById('confirm-delete-btn');
  if (delBtn) delBtn.addEventListener('click', confirmDelete);
});

/* ── Click delegation para a sidebar de conversas ── */
function onHistoryClick(e) {
  /* Ação no dropdown? */
  const action = e.target.closest('[data-action]');
  if (action) {
    e.stopPropagation();
    const act = action.dataset.action;
    const id  = parseInt(action.dataset.id, 10);
    if (act === 'open')   loadConversation(id);
    if (act === 'rename') openRename(id);
    if (act === 'delete') openDelete(id);
    return;
  }

  /* Botão `...` */
  const menuBtn = e.target.closest('.conv-menu-btn');
  if (menuBtn) {
    e.stopPropagation();
    const id = parseInt(menuBtn.dataset.id, 10);
    toggleConvMenu(id);
    return;
  }

  /* Linha da conversa → abrir */
  const item = e.target.closest('.chat-history-item');
  if (item) {
    const id = parseInt(item.dataset.id, 10);
    if (id) loadConversation(id);
  }
}

/* ── Conversations sidebar ── */
async function loadConversations() {
  const wrap = document.getElementById('chat-history');
  try {
    const res = await vexxAPI.get('/api/ai/conversations');
    _conversations = res.data || [];

    if (!_conversations.length) {
      wrap.innerHTML = '<div style="color:var(--text-faint);font-size:.78rem;padding:16px;text-align:center">Sem conversas ainda</div>';
      return;
    }

    wrap.innerHTML = _conversations.map(c => `
      <div class="chat-history-item ${c.id === _conversationId ? 'active' : ''}" data-id="${c.id}">
        <span class="conv-title">${esc(c.title || 'Sem título')}</span>
        <button class="conv-menu-btn" data-id="${c.id}" title="Opções" type="button">
          <i data-lucide="more-horizontal" size="14"></i>
        </button>
      </div>`).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('loadConversations:', err);
    wrap.innerHTML = '<div style="color:var(--red);padding:16px;font-size:.8rem">Erro ao carregar.</div>';
  }
}

function toggleConvMenu(id) {
  console.log('[ai] toggle menu for conv', id);
  const wasOpen = !!document.querySelector(`.conv-dropdown[data-conv-id="${id}"]`);
  closeAllDropdowns();
  if (wasOpen) return;  /* segundo clique fecha */

  const row = document.querySelector(`.chat-history-item[data-id="${id}"]`);
  if (!row) { console.warn('[ai] row not found for', id); return; }

  row.classList.add('menu-open');

  const dropdown = document.createElement('div');
  dropdown.className = 'conv-dropdown';
  dropdown.dataset.convId = id;
  dropdown.innerHTML = `
    <button type="button" data-action="rename" data-id="${id}"><i data-lucide="edit-2" size="13"></i> Renomear</button>
    <button type="button" data-action="open"   data-id="${id}"><i data-lucide="external-link" size="13"></i> Abrir</button>
    <button type="button" class="danger" data-action="delete" data-id="${id}"><i data-lucide="trash-2" size="13"></i> Excluir</button>
  `;
  row.appendChild(dropdown);
  if (window.lucide) lucide.createIcons();
}

function closeAllDropdowns() {
  document.querySelectorAll('.conv-dropdown').forEach(el => el.remove());
  document.querySelectorAll('.chat-history-item.menu-open').forEach(el => el.classList.remove('menu-open'));
}

async function loadConversation(id) {
  closeAllDropdowns();
  _conversationId = id;
  try {
    const res = await vexxAPI.get(`/api/ai/conversations/${id}`);
    _messages = res.data?.messages || [];
    renderMessages();
    document.querySelectorAll('.chat-history-item').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.id, 10) === id);
    });
  } catch (err) {
    console.error('loadConversation:', err);
    showToast('Erro ao abrir conversa', 'error');
  }
}

function newConversation() {
  _conversationId = null;
  _messages = [];
  document.getElementById('chat-messages').innerHTML = `
    <div class="ai-card" style="margin:auto;max-width:560px;text-align:center">
      <div class="ai-avatar-wrap" style="margin:0 auto 16px"><div class="ai-orb"></div><div class="ai-avatar-icon"><i data-lucide="bot" size="22"></i></div></div>
      <h3 class="widget-title" style="font-size:1.05rem">Nova conversa</h3>
      <p class="widget-subtitle">Faça uma pergunta sobre seu negócio para começar.</p>
      <div class="ai-quick-grid" style="grid-template-columns:1fr 1fr;gap:8px;margin-top:18px">
        <button class="ai-quick" onclick="quickAsk('Qual minha margem de lucro este mês?')"><i data-lucide="trending-up" size="13"></i> Margem de lucro</button>
        <button class="ai-quick" onclick="quickAsk('Quantos leads novos tive nos últimos 30 dias?')"><i data-lucide="target" size="13"></i> Leads novos</button>
        <button class="ai-quick" onclick="quickAsk('Como está meu pipeline de vendas?')"><i data-lucide="git-branch" size="13"></i> Pipeline</button>
        <button class="ai-quick" onclick="quickAsk('Faça um resumo executivo do negócio')"><i data-lucide="file-text" size="13"></i> Resumo executivo</button>
      </div>
    </div>`;
  if (window.lucide) lucide.createIcons();
  document.querySelectorAll('.chat-history-item').forEach(el => el.classList.remove('active'));
  document.getElementById('chat-input').focus();
}

/* ── Rename ── */
function openRename(id) {
  closeAllDropdowns();
  const conv = _conversations.find(c => c.id === id);
  if (!conv) return;
  _renameTargetId = id;
  document.getElementById('rename-input').value = conv.title || '';
  openModal('rename-modal');
  setTimeout(() => document.getElementById('rename-input').select(), 100);
}

async function confirmRename(e) {
  e.preventDefault();
  const newTitle = document.getElementById('rename-input').value.trim();
  if (!newTitle || !_renameTargetId) return;

  try {
    await vexxAPI.request('PATCH', `/api/ai/conversations/${_renameTargetId}`, { title: newTitle });
    showToast('Conversa renomeada', 'success');
    closeModal('rename-modal');
    const conv = _conversations.find(c => c.id === _renameTargetId);
    if (conv) conv.title = newTitle;
    loadConversations();
  } catch (err) {
    console.error('rename:', err);
    showToast(err.message || 'Erro ao renomear', 'error');
  }
}

/* ── Delete ── */
function openDelete(id) {
  closeAllDropdowns();
  const conv = _conversations.find(c => c.id === id);
  if (!conv) return;
  _deleteTargetId = id;
  document.getElementById('delete-conv-title').textContent = conv.title || 'Sem título';
  openModal('delete-modal');
}

async function confirmDelete() {
  if (!_deleteTargetId) return;
  const id = _deleteTargetId;
  console.log('Excluindo conversa', id);

  try {
    await vexxAPI.delete(`/api/ai/conversations/${id}`);
    showToast('Conversa excluída', 'success');
    closeModal('delete-modal');

    _conversations = _conversations.filter(c => c.id !== id);
    document.querySelector(`.chat-history-item[data-id="${id}"]`)?.remove();

    if (_conversationId === id) newConversation();
    if (!_conversations.length) loadConversations();

    _deleteTargetId = null;
  } catch (err) {
    console.error('delete error:', err);
    showToast(err.message || 'Erro ao excluir', 'error');
  }
}

/* ── Messaging ── */
function renderMessages() {
  const wrap = document.getElementById('chat-messages');
  if (!_messages.length) { wrap.innerHTML = ''; return; }
  wrap.innerHTML = _messages.map(m => {
    const isUser = m.role === 'user';
    return `
      <div class="chat-msg ${isUser ? 'user' : 'assistant'}">
        <div class="chat-msg-avatar">${isUser ? 'EU' : 'AI'}</div>
        <div class="chat-msg-content">${formatMsg(m.content)}</div>
      </div>`;
  }).join('');
  wrap.scrollTop = wrap.scrollHeight;
}

function appendMessage(role, content) {
  _messages.push({ role, content });
  const wrap = document.getElementById('chat-messages');
  if (_messages.length === 1) wrap.innerHTML = '';
  const div = document.createElement('div');
  div.className = `chat-msg ${role === 'user' ? 'user' : 'assistant'}`;
  div.innerHTML = `
    <div class="chat-msg-avatar">${role === 'user' ? 'EU' : 'AI'}</div>
    <div class="chat-msg-content">${formatMsg(content)}</div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return div;
}

function appendTyping() {
  const wrap = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg assistant';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="chat-msg-avatar">AI</div>
    <div class="chat-msg-content"><div class="ai-typing"><span></span><span></span><span></span></div></div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
}

function formatMsg(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:var(--surface-lg);padding:1px 5px;border-radius:4px;font-size:.85em">$1</code>')
    .replace(/\n/g, '<br>');
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  appendMessage('user', message);
  input.value = '';
  input.style.height = 'auto';
  appendTyping();

  try {
    const res = await vexxAPI.post('/api/ai/chat', { message, conversation_id: _conversationId });
    document.getElementById('typing-indicator')?.remove();
    if (res.data) {
      const isNew = !_conversationId;
      _conversationId = res.data.conversation_id;
      appendMessage('assistant', res.data.reply);
      if (isNew) loadConversations();
    }
  } catch (err) {
    document.getElementById('typing-indicator')?.remove();
    appendMessage('assistant', `⚠️ ${err.message || 'Erro ao processar mensagem.'}\n\nVerifique se você cadastrou uma API key em **Configurações → API Keys**.`);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function quickAsk(text) {
  document.getElementById('chat-input').value = text;
  sendMessage();
}

function onChatKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  autoResizeInput();
}

function autoResizeInput() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

function esc(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
