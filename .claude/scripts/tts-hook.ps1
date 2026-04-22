param()

$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }

try {
    $payload = $raw | ConvertFrom-Json
} catch {
    exit 0
}

$transcript = $payload.transcript_path
if (-not $transcript -or -not (Test-Path $transcript)) { exit 0 }

$lastText = $null
try {
    Get-Content -LiteralPath $transcript -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        try {
            $msg = $line | ConvertFrom-Json
        } catch { return }

        $role = $msg.message.role
        if (-not $role) { $role = $msg.role }
        if ($role -ne 'assistant') { return }

        $content = $msg.message.content
        if (-not $content) { $content = $msg.content }
        if (-not $content) { return }

        $parts = @()
        if ($content -is [string]) {
            $parts += $content
        } else {
            foreach ($block in $content) {
                if ($block.type -eq 'text' -and $block.text) {
                    $parts += $block.text
                } elseif ($block -is [string]) {
                    $parts += $block
                }
            }
        }
        $joined = ($parts -join "`n").Trim()
        if ($joined) { $script:lastText = $joined }
    }
} catch {
    exit 0
}

if (-not $lastText) { exit 0 }

$baseUrl = $env:MANAGER_AI_BASE_URL
if (-not $baseUrl) { $baseUrl = 'http://localhost:8000' }

function Get-SettingsMap {
    param([string]$BaseUrl)
    try {
        $list = Invoke-RestMethod -Uri "$BaseUrl/api/settings" -Method Get -TimeoutSec 5
    } catch {
        return $null
    }
    $map = @{}
    foreach ($s in $list) { $map[$s.key] = $s.value }
    return $map
}

function ConvertTo-CmdArg {
    param([string]$Value)
    if ($null -eq $Value) { return '""' }
    # Windows CRT argv quoting: escape backslashes before quotes, escape quotes, wrap in quotes.
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    $chars = $Value.ToCharArray()
    $i = 0
    while ($i -lt $chars.Length) {
        $backslashes = 0
        while ($i -lt $chars.Length -and $chars[$i] -eq '\') {
            $backslashes++
            $i++
        }
        if ($i -eq $chars.Length) {
            [void]$sb.Append('\' * ($backslashes * 2))
            break
        } elseif ($chars[$i] -eq '"') {
            [void]$sb.Append('\' * ($backslashes * 2 + 1))
            [void]$sb.Append('"')
            $i++
        } else {
            [void]$sb.Append('\' * $backslashes)
            [void]$sb.Append($chars[$i])
            $i++
        }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Invoke-HaikuSummarize {
    param(
        [string]$Text,
        [string]$Prompt,
        [string]$Model,
        [int]$TimeoutSeconds
    )

    $claudeExe = $null
    try {
        $resolved = & where.exe claude 2>$null | Select-Object -First 1
        if ($resolved) { $claudeExe = $resolved.Trim() }
    } catch {}
    if (-not $claudeExe) {
        $cmd = Get-Command claude -ErrorAction SilentlyContinue
        if ($cmd) { $claudeExe = $cmd.Source }
    }
    if (-not $claudeExe) { return $null }

    # where.exe / Get-Command may return .cmd/.ps1 shim; ProcessStartInfo needs a launchable file.
    # For .cmd shims spawn via cmd.exe; otherwise run directly.
    $ext = [System.IO.Path]::GetExtension($claudeExe).ToLowerInvariant()

    $workDir = $env:TEMP
    if (-not $workDir) { $workDir = [System.IO.Path]::GetTempPath() }

    $argString = (ConvertTo-CmdArg '-p') + ' ' + `
                 (ConvertTo-CmdArg $Prompt) + ' ' + `
                 (ConvertTo-CmdArg '--model') + ' ' + `
                 (ConvertTo-CmdArg $Model) + ' ' + `
                 (ConvertTo-CmdArg '--dangerously-skip-permissions') + ' ' + `
                 (ConvertTo-CmdArg '--output-format') + ' ' + `
                 (ConvertTo-CmdArg 'text')

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    if ($ext -eq '.cmd' -or $ext -eq '.bat') {
        $psi.FileName = $env:ComSpec
        if (-not $psi.FileName) { $psi.FileName = 'cmd.exe' }
        $psi.Arguments = '/c ' + (ConvertTo-CmdArg $claudeExe) + ' ' + $argString
    } else {
        $psi.FileName = $claudeExe
        $psi.Arguments = $argString
    }
    $psi.WorkingDirectory = $workDir
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    $proc = $null
    try {
        $proc = [System.Diagnostics.Process]::Start($psi)
        if (-not $proc) { return $null }

        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        try {
            $proc.StandardInput.Write($Text)
            $proc.StandardInput.Close()
        } catch {}

        if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
            try { $proc.Kill() } catch {}
            return $null
        }
        if ($proc.ExitCode -ne 0) { return $null }

        $out = $stdoutTask.Result
        if (-not $out) { return $null }
        $out = $out.Trim()
        if (-not $out) { return $null }
        return $out
    } catch {
        if ($proc -and -not $proc.HasExited) {
            try { $proc.Kill() } catch {}
        }
        return $null
    } finally {
        if ($proc) { $proc.Dispose() }
    }
}

$finalText = $lastText

$settings = Get-SettingsMap -BaseUrl $baseUrl
if ($settings) {
    $summarizeEnabled = ($settings['tts.summarize_enabled'] -eq 'true')
    if ($summarizeEnabled) {
        $model = $settings['tts.summarize_model']
        if (-not $model) { $model = 'claude-haiku-4-5-20251001' }

        $promptTemplate = $settings['tts.summarize_prompt']
        if (-not $promptTemplate) {
            $promptTemplate = 'Riassumi il seguente testo per la lettura vocale in italiano. Scrivi in prosa scorrevole, massimo {max_length} parole. Niente code block, niente liste puntate, niente markdown. Se ci sono comandi o nomi di file leggili come testo normale.'
        }

        $maxLength = 60
        if ($settings['tts.summarize_max_length']) {
            try { $maxLength = [int]$settings['tts.summarize_max_length'] } catch {}
        }

        $timeoutSeconds = 10
        if ($settings['tts.summarize_timeout_seconds']) {
            try { $timeoutSeconds = [int]$settings['tts.summarize_timeout_seconds'] } catch {}
        }

        $prompt = $promptTemplate -replace '\{max_length\}', [string]$maxLength

        try {
            Push-Location ([System.IO.Path]::GetTempPath())
            $summary = Invoke-HaikuSummarize -Text $lastText -Prompt $prompt -Model $model -TimeoutSeconds $timeoutSeconds
        } catch {
            $summary = $null
        } finally {
            try { Pop-Location } catch {}
        }

        if ($summary) { $finalText = $summary }
    }
}

$body = @{
    type        = 'tts'
    text        = $finalText
    terminal_id = $env:MANAGER_AI_TERMINAL_ID
    issue_id    = $env:MANAGER_AI_ISSUE_ID
    project_id  = $env:MANAGER_AI_PROJECT_ID
} | ConvertTo-Json -Compress -Depth 4

try {
    Invoke-RestMethod -Uri "$baseUrl/api/events" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5 | Out-Null
} catch {
    # swallow — hook must never break Claude Code
}

exit 0
