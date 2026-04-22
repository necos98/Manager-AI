@echo off
REM ============================================================
REM Notifica Manager AI
REM Usage: notify.bat "Titolo" "Messaggio"
REM Le env var MANAGER_AI_* vengono ereditate dal processo chiamante
REM ============================================================

SET TITLE=%~1
SET MESSAGE=%~2

IF "%TITLE%"=="" SET TITLE=Claude
IF "%MESSAGE%"=="" SET MESSAGE=Operazione completata

IF "%MANAGER_AI_BASE_URL%"=="" SET MANAGER_AI_BASE_URL=http://localhost:8000

powershell.exe -NoProfile -Command ^
  "$body = @{type='notification'; title='%TITLE%'; message='%MESSAGE%'; terminal_id='%MANAGER_AI_TERMINAL_ID%'; issue_id='%MANAGER_AI_ISSUE_ID%'; project_id='%MANAGER_AI_PROJECT_ID%'} | ConvertTo-Json; " ^
  "try { Invoke-RestMethod -Uri '%MANAGER_AI_BASE_URL%/api/events' -Method Post -ContentType 'application/json' -Body $body | Out-Null } catch {}"
