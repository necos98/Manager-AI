# Specification: Fix Claude Code Hook Execution with Internal Python Scripts

## Problem

Claude Code hooks defined in `.claude/settings.json` currently use `powershell.exe` to execute `.ps1` scripts injected via `claude_resources/`. These scripts fail because:

1. **`cygpath` dependency**: Hook commands use `$(cygpath -w "$(pwd)")` to resolve paths, which only works in Cygwin/MSYS2 environments. On standard Windows (PowerShell, cmd) the command silently fails.
2. **Character escaping in `notify.bat`**: `notify-hook.ps1` delegates to `notify.bat`, which embeds `%TITLE%` and `%MESSAGE%` into a PowerShell one-liner. Special characters (quotes, ampersands, backticks) break the command.
3. **Complex PS1 logic**: TTS hook has ~240 lines of PowerShell doing JSONL parsing, HTTP calls, subprocess management — fragile and hard to maintain.

## Solution

Replace PS1 scripts with Python scripts in `claude_resources/scripts/`. Same architecture — scripts are injected into `.claude/scripts/` per project via existing `install_claude_resources` endpoint. Hook commands in `settings.json` call `python` instead of `powershell.exe`.

### Files

| Action | File |
|--------|------|
| **NEW** | `claude_resources/scripts/notify-hook.py` |
| **NEW** | `claude_resources/scripts/tts-hook.py` |
| **MODIFY** | `claude_resources/settings.json` |
| **DELETE** | `claude_resources/scripts/notify-hook.ps1` |
| **DELETE** | `claude_resources/scripts/tts-hook.ps1` |
| **DELETE** | `claude_resources/scripts/notify.bat` |

### notify-hook.py

- Read JSON from stdin: `{"title": "...", "message": "..."}`
- Fallback: CLI args `--default-title` / `--default-message`
- POST to `$MANAGER_AI_BASE_URL/api/events` via `urllib.request`
- Body: `{"type": "notification", "title": ..., "message": ..., "terminal_id": ..., "issue_id": ..., "project_id": ...}`
- All errors caught silently (hook must not break Claude Code)
- ~40 lines, stdlib only

### tts-hook.py

- Read JSON from stdin: `{"transcript_path": "/path/to/transcript.jsonl"}`
- Parse JSONL transcript file, extract last `role=assistant` message text
- Fetch `/api/settings` for TTS config (`tts.summarize_enabled`, `tts.summarize_model`, `tts.summarize_prompt`, `tts.summarize_max_length`, `tts.summarize_timeout_seconds`)
- If summarize enabled: spawn `claude` subprocess (text via stdin, output via stdout) using model from settings
- POST final text to `$MANAGER_AI_BASE_URL/api/events` with type `tts`
- All errors caught silently
- ~120 lines, stdlib only

### settings.json

Hook commands replace powershell with python, remove cygpath:

**Stop hooks:**
```
python -I .claude/scripts/notify-hook.py --default-title "Claude finished" --default-message "Response complete"
python -I .claude/scripts/tts-hook.py
```

**Notification hook:**
```
python -I .claude/scripts/notify-hook.py --default-title "Claude attention" --default-message "Awaiting input"
```

Relative path `.claude/scripts/` resolves from project root (Claude Code's working directory).

### Dependencies

- `python` must be on PATH (already true for development environments)
- `urllib.request`, `json`, `sys`, `os`, `subprocess`, `argparse` — all stdlib
- No pip packages needed

## What does NOT change

- `install_claude_resources` endpoint — copies files as-is, no logic changes needed
- `settings.json` hook event names (Stop, Notification) and matcher — unchanged
- Manager AI backend event ingestion — unchanged
- Hook execution model — scripts still read stdin, communicate via env vars and HTTP
