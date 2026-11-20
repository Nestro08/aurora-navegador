@echo off
rem Construye Aurora.exe (dist\Aurora), el instalador (dist\Aurora-Setup-<version>.exe, con Inno Setup 6)
rem y deja en dist todo lo que hay que subir a una Release de GitHub (ver herramientas\preparar_release.py).
setlocal
cd /d "%~dp0"
echo.
echo  ===  Aurora: construir el programa para Windows  ===
echo.
where python >nul 2>nul
if errorlevel 1 (
    echo No encuentro Python. Instalalo desde https://www.python.org y marca "Add python.exe to PATH".
    pause
    exit /b 1
)
if not exist .venv (
    echo Creando entorno virtual...
    python -m venv .venv || goto error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller pillow || goto error
python herramientas\version.py || goto error
python herramientas\crear_icono.py || goto error
pyinstaller --noconfirm --clean Aurora.spec || goto error
echo.
echo  Programa listo: dist\Aurora\Aurora.exe
echo.
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
    "%ISCC%" instalador\aurora.iss || goto error
    echo.
    echo  Instalador listo en la carpeta dist
) else (
    echo  Para crear tambien el instalador, instala Inno Setup 6 desde
    echo  https://jrsoftware.org/isdl.php y vuelve a ejecutar construir.bat
)
echo.
python herramientas\preparar_release.py || goto error
echo.
pause
exit /b 0

:error
echo.
echo  Algo ha fallado. Revisa los mensajes de arriba.
pause
exit /b 1
