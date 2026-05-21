## Changes

### `backend/app/routers/projects.py`
- Extracted `install_claude_resources_to(project_path: str) -> dict` helper function from the inline endpoint logic
- Refactored `POST /{project_id}/install-claude-resources` to delegate to the new helper

### `backend/app/main.py`
- Imported `install_claude_resources_to` from `app.routers.projects`
- Added startup loop in lifespan: after plugins start, calls `install_claude_resources_to(p.path)` for every project
- Wrapped in nested try/except: per-project failures log a warning; outer catch ensures startup continues

## Result
On server start, all projects get fresh `claude_resources/` copied to their `.claude/` directory automatically. Same effect as clicking "Reinstall" per project in the health panel.