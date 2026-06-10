@echo off
title Hermes Gateway - Fix No Console Window

:: Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ========================================
    echo   Servono privilegi di amministratore
    echo ========================================
    echo.
    echo Tasto destro sul file -^> "Esegui come amministratore"
    echo.
    pause
    exit /b 1
)

echo ========================================
echo   Hermes Gateway - Fix No Console Window
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%fix-gateway-no-console.ps1"

if not exist "%PS_SCRIPT%" (
    echo [ERRORE] File non trovato:
    echo   %PS_SCRIPT%
    pause
    exit /b 1
)

echo Avvio lo script PowerShell...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

echo.
pause
