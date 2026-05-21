# Specification: Fix Hook Scripts Path Resolution

## Problem

Claude Code stop hooks fail with "No such file or directory" for:
- `.claude/scripts/notify-hook.py`
- `.claude/scripts/tts-hook.py`

The scripts **exist** at `<project_root>/.claude/scripts/` but Claude Code's working directory when executing Stop hooks is `backend/`, so the relative path resolves to `backend/.claude/scripts/` which does not exist.

## Root Cause

`settings.json` defines hook commands using relative paths:
```json
"command": "python -I .claude/scripts/notify-hook.py --default-title \"Claude finished\" --default-message \"Response complete\""
```

The assumption was that Claude Code's CWD during hook execution is the project root. It is actually the `backend/` subdirectory (where the terminal/process that launched Claude Code was running).

## Fix Strategy

Make hook script paths independent of CWD. Use `CLAUDE_PROJECT_DIR` environment variable (set by Claude Code during hook execution) to construct absolute paths.

### Changes Required

**1. `claude_resources/settings.json`** (source of truth) and **`.claude/settings.json`** (installed copy)

Change all three hook command entries from relative paths to absolute paths using `CLAUDE_PROJECT_DIR`:

**Stop hook — notify:**
```json
"command": "python -I \"$env:CLAUDE_PROJECT_DIR\\.claude\\scripts\\notify-hook.py\" --default-title \"Claude finished\" --default-message \"Response complete\""
```

**Stop hook — tts:**
```json
"command": "python -I \"$env:CLAUDE_PROJECT_DIR\\.claude\\scripts\\tts-hook.py\""
```

**Notification hook — notify:**
```json
"command": "python -I \"$env:CLAUDE_PROJECT_DIR\\.claude\\scripts\\notify-hook.py\" --default-title \"Claude attention\" --default-message \"Awaiting input\""
```

Note: Uses PowerShell syntax (`$env:VAR`) since Windows is the deployment platform. If cross-platform support is needed, a wrapper script should be used instead.

### Acceptance Criteria

1. Stop hooks fire successfully after a Claude Code session ends
2. Notification hooks fire successfully when Claude Code awaits user input
3. Hook scripts execute regardless of CWD at hook execution time
4. Same fix is applied to both `claude_resources/settings.json` (source) and `.claude/settings.json` (installed copy)