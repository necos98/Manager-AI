## What was done

Changed 3 hook command paths in `claude_resources/settings.json` from relative (`.claude/scripts/...`) to absolute using `$env:CLAUDE_PROJECT_DIR`:

1. **Stop hook — notify:** `python -I "$env:CLAUDE_PROJECT_DIR\.claude\scripts\notify-hook.py" --default-title "Claude finished" --default-message "Response complete"`
2. **Stop hook — tts:** `python -I "$env:CLAUDE_PROJECT_DIR\.claude\scripts\tts-hook.py"`
3. **Notification hook — notify:** `python -I "$env:CLAUDE_PROJECT_DIR\.claude\scripts\notify-hook.py" --default-title "Claude attention" --default-message "Awaiting input"`

Synced `.claude/settings.json` from source. The app auto-syncs at startup via `install_claude_resources_to()`.

## Root cause

Claude Code's CWD during hook execution is `backend/`, not project root. Relative paths resolved to `backend/.claude/scripts/` which doesn't exist.

## Key decisions

- Only edited `claude_resources/settings.json` (source of truth). `.claude/settings.json` is a generated copy.
- Used `$env:CLAUDE_PROJECT_DIR` (PowerShell syntax) — env var set by Claude Code during hook execution, points to project root.
- Windows-specific: `\\` path separators inside JSON strings.