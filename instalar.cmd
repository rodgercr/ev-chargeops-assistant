@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   GOODWE AI - INSTALACAO DO AMBIENTE
echo ==============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado. Instale o Python 3.11 ou superior.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -m venv .venv
    if errorlevel 1 goto :erro
)

echo Instalando dependencias...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo.
    echo Arquivo .env criado. Preencha DATABASE_URL e SECRET_KEY antes de executar.
)

echo.
echo Instalacao concluida.
echo Proximo passo: configure o .env e execute preparar_rag.cmd.
pause
exit /b 0

:erro
echo.
echo Ocorreu um erro durante a instalacao.
pause
exit /b 1
