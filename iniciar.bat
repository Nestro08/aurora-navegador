@echo off
rem Ejecuta Aurora sin construir el .exe (instala las dependencias la primera vez).
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
start "" pythonw Aurora.pyw %*
