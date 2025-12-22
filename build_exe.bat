@echo off
echo ========================================
echo  Build do Transcritor de Videos YouTube
echo ========================================
echo.

REM Verifica se PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo.
echo Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist transcreva.spec del transcreva.spec

echo.
echo Construindo executavel...
echo.

REM Build com PyInstaller usando arquivo .spec (melhor controle)
if exist transcreva.spec (
    pyinstaller --clean --log-level=ERROR transcreva.spec
) else (
    pyinstaller --name="TranscritorYouTube" ^
        --onefile ^
        --windowed ^
        --noupx ^
        --hidden-import=whisper ^
        --hidden-import=yt_dlp ^
        --hidden-import=yt_dlp.extractor ^
        --hidden-import=yt_dlp.downloader ^
        --hidden-import=tkinter ^
        --hidden-import=tkinter.ttk ^
        --hidden-import=tkinter.filedialog ^
        --hidden-import=tkinter.messagebox ^
        --hidden-import=tkinter.scrolledtext ^
        --collect-all=whisper ^
        --collect-all=yt_dlp ^
        --clean ^
        --log-level=ERROR ^
        transcreva.py
)

if errorlevel 1 (
    echo.
    echo ERRO: Falha ao construir executavel!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build concluido com sucesso!
echo ========================================
echo.
echo O executavel esta em: dist\TranscritorYouTube.exe
echo.
pause

