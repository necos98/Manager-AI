# Auto-reinstall claude_resources on startup — Implementation Plan

**Goal:** Call `install_claude_resources` for every project on server startup, same as clicking "Reinstall" per project.

**Architecture:** Extract copy logic from the existing endpoint into a reusable helper. Call it from both the endpoint (unchanged behavior) and the main.py startup loop (new behavior).

**Files:**
- Modify: `backend/app/routers/projects.py` — extract `install_claude_resources_to()`, refactor endpoint
- Modify: `backend/app/main.py` — call helper per project on startup

---

### Task 1: Extract helper function in projects.py

**File:** `backend/app/routers/projects.py`

Move the copy logic (lines 363-382) into a module-level function `install_claude_resources_to(project_path: str)` that:
- Takes a project path string (not a DB object)
- Reads source from `_claude_resources_source()`
- Copies to `<project_path>/.claude/`, skipping dotfiles
- Returns `{"path": dest, "copied": [...]}`
- Raises `HTTPException(404)` if source dir missing

Refactor the existing `install_claude_resources` endpoint to:
- Validate project + dir (keep existing checks)
- Delegate to `install_claude_resources_to(project.path)`

---

### Task 2: Call helper on startup

**File:** `backend/app/main.py`

In the lifespan startup, after plugins are started for all projects, add a loop:

```python
for p in rows:
    try:
        result = install_claude_resources_to(p.path)
        logger.info("Installed claude_resources to %s: %s", p.path, result.get("copied"))
    except Exception:
        logger.warning("Failed to install claude_resources to %s", p.path, exc_info=True)
```

Wrap in try/except so one broken project doesn't crash startup.

---

### Task 3: Verify

Start the server and confirm `claude_resources` are copied to each project's `.claude/` directory at startup. Check logs for success/warning messages.