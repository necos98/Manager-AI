## Summary

Replaced PS1 Claude Code hook scripts with Python equivalents in `claude_resources/scripts/`.

### What changed

- **Deleted**: `notify-hook.ps1`, `tts-hook.ps1`, `notify.bat` from both `claude_resources/scripts/` and `.claude/scripts/`
- **Created**: `notify-hook.py` (~50 lines) — reads JSON from stdin, POSTs notification event to Manager AI via `urllib.request`. Falls back to `--default-title`/`--default-message` CLI args. All errors silently caught.
- **Created**: `tts-hook.py` (~130 lines) — reads JSON with `transcript_path` from stdin, parses JSONL transcript, extracts last assistant message, optionally summarizes via `claude -p` subprocess if `tts.summarize_enabled` setting is true, POSTs TTS event to Manager AI. All errors silently caught.
- **Modified**: `settings.json` — hook commands changed from `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$(pwd)")\.claude\scripts\..."` to `python -I .claude/scripts/...py`. Removes `cygpath` dependency. Uses relative paths from project root.

### Root cause of broken hooks

`$(cygpath -w "$(pwd)")` in hook commands only works in Cygwin/MSYS2. Standard Windows shells (PowerShell, cmd) resolve `cygpath` as unknown command, so hooks silently never executed.

### What was NOT changed

- `install_claude_resources` endpoint — unchanged, copies files as before
- Manager AI backend event ingestion — unchanged
- Hook event names, matchers, trigger conditions — unchanged
- All scripts stdlib-only (urllib, json, subprocess, argparse) — no new dependencies