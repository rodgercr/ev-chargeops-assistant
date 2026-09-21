@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   GOODWE AI - EV CHARGEOPS ASSISTANT
echo ==============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado.
    echo Execute instalar.cmd primeiro.
    pause
    exit /b 1
)

if not exist ".env" (
    echo Arquivo .env nao encontrado.
    echo Copie .env.example para .env e preencha as configuracoes.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m streamlit run streamlit_app.py --server.fileWatcherType none --browser.gatherUsageStats false

if errorlevel 1 (
    echo.
    echo Ocorreu um erro durante a execucao.
    pause
)
