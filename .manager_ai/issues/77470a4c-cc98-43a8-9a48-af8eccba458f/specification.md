## Extract `_load_project_into_memory` into `storage/project_loader.py`

### Scope

Extract the `_load_project_into_memory` function (main.py:118-288) and its module-level helper functions (main.py:291-331) into a new standalone module `backend/app/storage/project_loader.py`. The function loads all issues, memories, and file metadata from disk (.manager_ai/ directory structure) into the in-memory MemoryStore at startup and on-demand (project create, rebuild).

What moves:
- `_load_project_into_memory` function body (lines 118-288)
- Module-level helpers (lines 291-331): `_read_optional_md`, `_opt_str_static`, `_as_iso`, `_task_from_dict`, `_relation_from_dict`
- Nested closures inside the function body: `_FRONTMATTER_RE` regex, `_parse_fm`, `_opt_str`, `_as_str`, `_link_from_dict` — promote to module-level in the new file
- The `import re as _re` and other local imports stay inside the function body, with one exception: since `_FRONTMATTER_RE` becomes module-level, `import re` must be added at the module level of the new file

What stays in main.py:
- All other `_startup_*` functions
- The `_load_project_into_memory()` call sites in the lifespan (line 391)
- All other code

### Constraints

1. **Circular imports**: `_load_project_into_memory` imports store models locally inside the function body (`from app.storage.memory_store import MemoryRecord, MemoryLinkRecord`, etc.) to avoid circular imports between `app.main` and `app.storage.*`. The extracted module must preserve this same pattern — keep all store-model imports local inside the function body.

2. **Logger dependency**: The function uses `logger.warning()` and `logger.info()` (6 calls total). The new module needs its own `logger = logging.getLogger(__name__)` at module level, plus `import logging` at the top.

3. **Callers must work**: Two callers exist outside main.py — `app.routers.projects.py` lines 343-344 and 421-423. These currently import via `from app.main import _load_project_into_memory`. After extraction, update these to `from app.storage.project_loader import _load_project_into_memory`.

4. **Helper deduplication**: The nested closures `_opt_str`, `_as_str`, `_link_from_dict` plus module-level `_opt_str_static`, `_as_iso` are duplicated in `storage/memory_store.py` and `storage/file_store.py`. This extraction consolidates the copies inside the function into one place only. The copies in memory_store.py / file_store.py remain untouched (out of scope).

5. **Signature unchanged**: `_load_project_into_memory(project_path: str, store: Any) -> None` must remain identical. No behavioral changes.

6. **_FRONTMATTER_RE optimization**: Move `_FRONTMATTER_RE` regex from inside the function body to module-level (compiled once, not per-call). Must use `import re` at module level.

### Acceptance Criteria

- [ ] New file `backend/app/storage/project_loader.py` exists with `_load_project_into_memory`, all helpers, `logger = logging.getLogger(__name__)`, and `import re` at module level
- [ ] `main.py` no longer contains the function or its module-level helpers
- [ ] `main.py` imports `_load_project_into_memory` from the new module
- [ ] `projects.py` imports `_load_project_into_memory` from the new module
- [ ] All local imports for circular protection preserved inside function body
- [ ] `_FRONTMATTER_RE` compiled once at module level
- [ ] Function signature unchanged
- [ ] Startup sequence works: `python start.py` loads projects without errors
- [ ] Project rebuild works: API call to rebuild index works without errors

### Non-goals

- Do NOT refactor the duplicate helpers in `memory_store.py` or `file_store.py`
- Do NOT change function behavior or loading logic
- Do NOT rename the function
- Do NOT restructure the startup sequence or lifespan
- Do NOT add tests for this extraction (existing coverage is sufficient)
