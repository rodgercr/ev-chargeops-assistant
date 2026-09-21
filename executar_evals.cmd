@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado.
    echo Execute instalar.cmd antes dos evals.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "evals\run_evals.py" %*
set "CODIGO=%ERRORLEVEL%"
echo.
pause
exit /b %CODIGO%
