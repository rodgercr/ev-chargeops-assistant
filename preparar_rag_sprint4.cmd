@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" preparar_rag_sprint4.py %*
exit /b %errorlevel%
