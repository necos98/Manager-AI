# Self-elevate if not admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"" + $MyInvocation.MyCommand.Path + "`""
    Start-Process powershell -Verb RunAs -ArgumentList $arguments
    exit
}

Write-Output "=============================================="
Write-Output "  Hermes Gateway - Fix No Console Window"
Write-Output "=============================================="
Write-Output ""

# Ferma la vecchia task
Write-Output "[1/4] Fermo la vecchia task..."
schtasks /end /tn "Hermes_Gateway" 2>&1 | Out-Null
Start-Sleep -Seconds 2

# Elimina la vecchia task
Write-Output "[2/4] Rimuovo la vecchia task..."
schtasks /delete /tn "Hermes_Gateway" /f 2>&1 | Out-Null
Start-Sleep -Seconds 1

$username = $env:USERNAME
$userdomain = $env:USERDOMAIN

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>$username</Author>
    <Description>Hermes Agent Gateway - Messaging Platform Integration (Resilient, No Console)</Description>
    <URI>\Hermes_Gateway</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>$userdomain\$username</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <RestartOnFailure>
      <Count>999</Count>
      <Interval>PT1M</Interval>
    </RestartOnFailure>
    <StartWhenAvailable>true</StartWhenAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers>
    <LogonTrigger>
      <StartBoundary>2026-06-09T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </LogonTrigger>
    <CalendarTrigger>
      <StartBoundary>2026-06-09T00:00:00</StartBoundary>
      <Repetition>
        <Interval>PT10M</Interval>
        <Duration>P365D</Duration>
      </Repetition>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <Enabled>true</Enabled>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>C:\Users\$username\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe</Command>
      <Arguments>-m hermes_cli.main gateway run</Arguments>
      <WorkingDirectory>C:\Users\$username\AppData\Local\hermes</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Scrivi XML in UTF-16
$path = "$env:TEMP\Hermes_Gateway.xml"
$xml | Set-Content -Path $path -Encoding Unicode -Force

# Crea la nuova Scheduled Task
Write-Output "[3/4] Creo la nuova Scheduled Task (pythonw.exe diretta)..."
$result = schtasks /create /tn "Hermes_Gateway" /xml "$path" /f 2>&1
Write-Output "RESULT: $result"

if ($LASTEXITCODE -eq 0) {
    # Avvia il gateway
    Write-Output "[4/4] Avvio il gateway..."
    schtasks /run /tn "Hermes_Gateway" 2>&1 | Out-Null
} else {
    Write-Output "[ERRORE] Impossibile creare la Scheduled Task!"
}

# Pulizia
Remove-Item $path -Force -ErrorAction SilentlyContinue

Write-Output ""
Write-Output "=============================================="
Write-Output "  FATTO!"
Write-Output "  - Gateway esegue pythonw.exe DIRETTAMENTE"
Write-Output "  - NESSUNA finestra cmd ogni 10 minuti"
Write-Output "  - Watchdog PT10M silenzioso"
Write-Output "  - RestartOnFailure PT1M attivo"
Write-Output "=============================================="
Write-Output ""
Write-Output "Premi un tasto per chiudere..."
Read-Host
