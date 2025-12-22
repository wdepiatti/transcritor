#!/usr/bin/env python3
"""
Script para construir o executável do Transcritor de Vídeos do YouTube.
"""

import subprocess
import sys
import os
from pathlib import Path

def verificar_pyinstaller():
    """Verifica se PyInstaller está instalado."""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("PyInstaller não encontrado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True

def limpar_builds_anteriores():
    """Remove builds anteriores."""
    dirs_para_remover = ["build", "dist"]
    arquivos_para_remover = ["transcreva.spec"]
    
    for dir_name in dirs_para_remover:
        if os.path.exists(dir_name):
            print(f"Removendo {dir_name}...")
            import shutil
            shutil.rmtree(dir_name)
    
    for file_name in arquivos_para_remover:
        if os.path.exists(file_name):
            print(f"Removendo {file_name}...")
            os.remove(file_name)

def construir_executavel():
    """Constrói o executável usando PyInstaller."""
    print("\n" + "="*50)
    print("Construindo executável...")
    print("="*50 + "\n")
    
    # Usa arquivo .spec se existir, senão usa comando direto
    spec_file = Path("transcreva.spec")
    
    if spec_file.exists():
        # Usa arquivo .spec (mais controle)
        comando = [
            "pyinstaller",
            "--clean",
            "--log-level=ERROR",
            "transcreva.spec"
        ]
    else:
        # Comando direto (fallback)
        comando = [
            "pyinstaller",
            "--name=TranscritorYouTube",
            "--onefile",
            "--windowed",  # SEM CONSOLE - GUI apenas
            "--noupx",
            "--hidden-import=whisper",
            "--hidden-import=yt_dlp",
            "--hidden-import=yt_dlp.extractor",
            "--hidden-import=yt_dlp.downloader",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=tkinter.filedialog",
            "--hidden-import=tkinter.messagebox",
            "--hidden-import=tkinter.scrolledtext",
            "--collect-all=whisper",
            "--collect-all=yt_dlp",
            "--clean",
            "--log-level=ERROR",
            "transcreva.py"
        ]
    
    try:
        # Executa o build (mostra saída normalmente)
        result = subprocess.run(comando, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\n" + "="*50)
            print("✓ Build concluído com sucesso!")
            print("="*50)
            print(f"\nExecutável criado em: {os.path.abspath('dist/TranscritorYouTube.exe')}")
            print("\nTamanho aproximado: 200-500 MB (inclui Whisper e dependências)")
            return True
        else:
            print(f"\n✗ Erro ao construir executável")
            if result.stderr:
                print(f"Erro: {result.stderr}")
            if result.stdout:
                print(f"Saída: {result.stdout}")
            return False
    except Exception as e:
        print(f"\n✗ Erro ao construir executável: {e}")
        return False

def main():
    print("="*50)
    print("Build do Transcritor de Vídeos do YouTube")
    print("="*50)
    
    # Verificar PyInstaller
    if not verificar_pyinstaller():
        print("Erro: Não foi possível instalar PyInstaller")
        return 1
    
    # Limpar builds anteriores
    limpar_builds_anteriores()
    
    # Construir executável
    if construir_executavel():
        print("\n✓ Pronto! Você pode executar o arquivo .exe na pasta 'dist'")
        return 0
    else:
        print("\n✗ Falha ao construir executável")
        return 1

if __name__ == "__main__":
    sys.exit(main())

