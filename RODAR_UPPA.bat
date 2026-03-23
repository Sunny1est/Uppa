@echo off
REM Atalho para rodar Uppa! com verificação automática de dependências
title Uppa! - Inicializando...
cd /d "%~dp0"

REM Verificar e instalar dependências automaticamente
python check_dependencies.py
if errorlevel 1 (
    echo.
    echo ❌ Erro ao verificar/instalar dependências
    echo Por favor, execute: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Iniciar Uppa!
cls
echo 🦦 Iniciando Uppa!...
echo.
python src/main.py
pause
