param(
    [string]$DefaultTitle = 'Claude',
    [string]$DefaultMessage = 'Done'
)

$raw = [Console]::In.ReadToEnd()
$title = $DefaultTitle
$message = $DefaultMessage

if ($raw) {
    try {
        $data = $raw | ConvertFrom-Json
        if ($data.title)   { $title = $data.title }
        if ($data.message) { $message = $data.message }
    } catch {}
}

$projectDir = (Get-Location).Path
$script = Join-Path $projectDir 'claude_resources\scripts\notify.bat'
if (-not (Test-Path $script)) {
    $script = Join-Path $projectDir '.claude\scripts\notify.bat'
}

& $script $title $message
