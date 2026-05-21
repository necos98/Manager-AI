# Auto-reinstall claude_resources on startup for all projects

## Goal
When the Manager AI server starts, automatically copy `claude_resources/` (settings, skills, commands, scripts) into every project's `.claude/` directory. Same effect as clicking "Reinstall" on each project's health panel, but automatic on startup.

## Current state
- `POST /api/projects/{project_id}/install-claude-resources` copies `claude_resources/` → `<project_path>/.claude/` per project
- Copy logic is inline in the endpoint handler (projects.py lines 363-382)
- Startup (`main.py` lifespan) loads projects into memory but never calls this logic
- User must manually click "Reinstall" in the UI for each project after startup

## Design

### Extract helper function
Move the copy logic from the endpoint into a reusable module-level function:

```python
def install_claude_resources_to(project_path: str) -> dict:
    """Copy claude_resources/ into <project_path>/.claude/. Returns {path, copied}."""
```

- Source: `claude_resources/` at repo root (use existing `_claude_resources_source()` helper)
- Dest: `<project_path>/.claude/`
- Skips dotfiles (same as current)
- Returns `{"path": dest, "copied": [...]}` or raises on missing source

### Refactor existing endpoint
`POST /{project_id}/install-claude-resources` delegates to the new helper after validating project exists and has valid dir.

### Add startup call
In `main.py` lifespan, after the projects are loaded into memory and plugins started, loop through all projects and call `install_claude_resources_to(p.path)` for each. Wrap in try/except + warning log so one broken project doesn't crash startup.

## Scope
- Only `claude_resources` (not MCP or Playwright MCP)
- No UI changes
- No new endpoints
- No config/feature flags