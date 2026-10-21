@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Execute instalar.cmd primeiro.
    exit /b 1
)
".venv\Scripts\python.exe" -c "import ragas" >nul 2>&1
if errorlevel 1 (
    echo Instalando as dependencias opcionais de avaliacao...
    ".venv\Scripts\python.exe" -m pip install -r requirements-ragas.txt
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" "evals\run_sprint4.py" %*
exit /b %ERRORLEVEL%
