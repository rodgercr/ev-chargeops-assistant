@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================================
echo   GOODWE AI - PREPARACAO DO RAG
echo ==============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado.
    echo Execute instalar.cmd primeiro.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "preparar_rag.py" %*
set "CODIGO=%ERRORLEVEL%"

if not "%CODIGO%"=="0" (
    echo.
    echo Nao foi possivel preparar o RAG.
    echo Na primeira execucao, mantenha a internet ativa para baixar o modelo de embeddings.
) else (
    echo.
    echo O RAG esta pronto para uso.
)

pause
exit /b %CODIGO%
