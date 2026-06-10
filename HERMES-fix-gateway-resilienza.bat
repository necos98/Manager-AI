@echo off
title Hermes Gateway - Fix Resilienza

setlocal enabledelayedexpansion

echo ========================================
echo   Hermes Gateway - Fix Resilienza
echo ========================================
echo.
echo Questo script necessita di privilegi
echo di amministratore per funzionare.
echo.
echo 1. Chiudi questa finestra se non sei admin
echo 2. Tasto destro - Esegui come amministratore
echo.
echo ========================================
echo.

:: Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERRORE: Devi eseguire questo script come amministratore!
    echo Tasto destro sul file -^> "Esegui come amministratore"
    pause
    exit /b 1
)
echo [OK] Privilegi amministratore verificati
echo.

:: Paths
set "TASK_NAME=Hermes_Gateway"
set "SCRIPT_DIR=%~dp0"
set "XML_PATH=%SCRIPT_DIR%Hermes_Gateway.xml"
set "PS_SCRIPT=%SCRIPT_DIR%generate_xml.ps1"
set "HERMES_HOME=C:\Users\j.magarelli\AppData\Local\hermes"
set "GATEWAY_CALLBACK=%HERMES_HOME%\gateway-service\Hermes_Gateway.cmd"

:: Check that the gateway script exists
if not exist "%GATEWAY_CALLBACK%" (
    echo [ERRORE] Il file gateway.cmd non esiste in:
    echo   %GATEWAY_CALLBACK%
    echo.
    echo Prova prima: hermes gateway install --force
    pause
    exit /b 1
)
echo [OK] Gateway script trovato: %GATEWAY_CALLBACK%
echo.

:: [1] Ferma il task in esecuzione
echo [1/5] Fermo il task in esecuzione...
schtasks /end /tn "%TASK_NAME%" >nul 2>&1
timeout /t 2 /nobreak >nul
echo [OK]
echo.

:: [2] Rimuove vecchia Scheduled Task
echo [2/5] Rimuovo la vecchia Scheduled Task...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
timeout /t 1 /nobreak >nul
echo [OK]
echo.

:: [3] Genera il file XML della Scheduled Task
echo [3/5] Genero il file XML della Scheduled Task...
if not exist "%PS_SCRIPT%" (
    echo [ERRORE] File generate_xml.ps1 non trovato: %PS_SCRIPT%
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "& '%PS_SCRIPT%' | Set-Content '%XML_PATH%' -Encoding Unicode"
if %errorLevel% neq 0 (
    echo ERRORE: Impossibile generare il file XML!
    pause
    exit /b 1
)
echo [OK] XML generato con utente: %USERDOMAIN%\%USERNAME%
echo.

:: [4] Crea la nuova Scheduled Task resiliente
echo [4/5] Creo la nuova Scheduled Task resiliente...
schtasks /create /tn "%TASK_NAME%" /xml "%XML_PATH%" /f
if %errorLevel% neq 0 (
    echo.
    echo ERRORE: Impossibile creare la Scheduled Task!
    echo.
    echo Possibili cause:
    echo   - Accesso negato: esegui come amministratore
    echo   - XML danneggiato: verifica %XML_PATH%
    pause
    exit /b 1
)
echo [OK] Scheduled Task creata con successo!
echo.

:: [5] Avvia il gateway
echo [5/5] Avvio il gateway...
schtasks /run /tn "%TASK_NAME%" >nul 2>&1
if %errorLevel% neq 0 (
    echo [AVVISO] Impossibile avviare il gateway automaticamente.
    echo          Puoi avviarlo manualmente con: hermes gateway run
) else (
    echo [OK] Gateway avviato!
)

echo.
echo ========================================
echo   FATTO! Il gateway ora e' resiliente:
echo   - Auto-restart ogni 1 minuto se cade
echo   - Watchdog ogni 10 minuti
echo   - Nessun limite di tempo
echo   - Non si ferma per batteria
echo ========================================
echo.
echo Apri Telegram e scrivi /start al bot!
echo.
pause
