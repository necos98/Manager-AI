# Implementation Plan: Fix Hook Scripts Path Resolution

**Goal:** Fix hook scripts so they resolve correctly regardless of CWD during hook execution.

**Architecture:** Replace relative paths in `claude_resources/settings.json` with absolute paths using `$env:CLAUDE_PROJECT_DIR` (PowerShell env var set by Claude Code during hook execution). Only the source file needs changing — `.claude/settings.json` is auto-generated at startup via `install_claude_resources_to()`.

**Tech Stack:** JSON config, PowerShell env var syntax

---

## Background

Claude Code's working directory during Stop/Notification hook execution is `backend/`, not the project root. Relative paths (`.claude/scripts/notify-hook.py`) resolve to `backend/.claude/scripts/` which doesn't exist.

`CLAUDE_PROJECT_DIR` env var is set by Claude Code during hook execution and points to the project root.

## Changes

**Single file to modify:** `claude_resources/settings.json`

Three hook commands need updating:

1. Stop hook — notify: `python -I .claude/scripts/notify-hook.py ...` → `python -I "$env:CLAUDE_PROJECT_DIR\.claude\scripts\notify-hook.py" ...`
2. Stop hook — tts: `python -I .claude/scripts/tts-hook.py` → `python -I "$env:CLAUDE_PROJECT_DIR\.claude\scripts\tts-hook.py"`
3. Notification hook — notify: `python -I .claude/scripts/notify-hook.py ...` → `python -I "$env:CLAUDE_PROJECT_DIR\.claude\scripts\notify-hook.py" ...`

`.claude/settings.json` will be regenerated from the source on next app startup (via `install_claude_resources_to()`).

## Verification

After the fix, restart the app to trigger `install_claude_resources_to()`. Then run a Claude Code session and verify:
- Stop hooks fire without "No such file or directory" errors
- Notification hooks fire when Claude Code awaits input