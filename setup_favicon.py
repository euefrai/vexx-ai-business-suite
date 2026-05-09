import os
import glob
from PIL import Image

def setup_favicon():
    # 1. Resize and save favicon
    img_path = 'ico-business.png'
    if not os.path.exists(img_path):
        print(f"Erro: Imagem {img_path} não encontrada na pasta raiz.")
        return

    try:
        print("Lendo imagem...")
        img = Image.open(img_path)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        
        # Save as PNG
        img.save('frontend/favicon.png', format='PNG')
        print("✓ Favicon salvo em frontend/favicon.png")
        
        # Save as ICO (for maximum compatibility)
        img.save('frontend/favicon.ico', format='ICO')
        print("✓ Favicon salvo em frontend/favicon.ico")
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        return

    # 2. Add favicon to all HTML files
    html_files = glob.glob('frontend/*.html')
    favicon_tag = '  <link rel="icon" href="/favicon.png" type="image/png">\n'
    
    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'favicon.png' not in content and 'favicon.ico' not in content:
            # Encontrar a tag <head> ou <title> para inserir logo depois
            if '<title>' in content:
                # Inserir depois do title
                parts = content.split('</title>')
                new_content = parts[0] + '</title>\n' + favicon_tag + parts[1]
            elif '<head>' in content:
                parts = content.split('<head>')
                new_content = parts[0] + '<head>\n' + favicon_tag + parts[1]
            else:
                continue
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ Favicon adicionado em {os.path.basename(file_path)}")

    print("\nTudo pronto! O favicon foi gerado e configurado no site inteiro.")

if __name__ == '__main__':
    setup_favicon()
