# Implementation Plan

3 scripts replaced, no backend changes, no new tests (scripts are standalone executables called by Claude Code, verified manually).

## Task 1: Delete old PS1 and bat scripts

Remove 3 files from `claude_resources/scripts/`:
- `notify-hook.ps1`
- `tts-hook.ps1`
- `notify.bat`

## Task 2: Create notify-hook.py

New file `claude_resources/scripts/notify-hook.py`:
- Read stdin for JSON `{title, message}`, fallback to CLI args `--default-title`/`--default-message`
- POST to `$MANAGER_AI_BASE_URL/api/events` with type=notification
- Include env vars: MANAGER_AI_TERMINAL_ID, MANAGER_AI_ISSUE_ID, MANAGER_AI_PROJECT_ID
- All errors caught silently (exit 0 always)

## Task 3: Create tts-hook.py

New file `claude_resources/scripts/tts-hook.py`:
- Read stdin for JSON `{transcript_path}`
- Parse JSONL transcript, extract last assistant message text
- Fetch `/api/settings` for TTS config
- If summarize enabled: spawn `claude -p` subprocess with text on stdin
- POST final text to `$MANAGER_AI_BASE_URL/api/events` with type=tts
- All errors caught silently (exit 0 always)

## Task 4: Update settings.json

Replace powershell hook commands with python:
- Stop hooks: `python -I .claude/scripts/notify-hook.py --default-title "..." --default-message "..."`
- Stop hooks: `python -I .claude/scripts/tts-hook.py`
- Notification hook: `python -I .claude/scripts/notify-hook.py --default-title "..." --default-message "..."`
- Remove cygpath dependency

## Task 5: Manual verification

Run scripts from command line with mock input:
- `echo '{"title":"test","message":"hello"}' | python claude_resources/scripts/notify-hook.py`
- Verify no errors, exit code 0
