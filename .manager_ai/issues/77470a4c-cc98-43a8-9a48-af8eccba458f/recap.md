Extracted `_load_project_into_memory` (170-line function + 5 module-level helpers) from `main.py` into new module `backend/app/storage/project_loader.py`.

Changes:
- Created `backend/app/storage/project_loader.py` with extracted function, helpers (`_read_optional_md`, `_opt_str_static`, `_as_iso`, `_task_from_dict`, `_relation_from_dict`), and promoted module-level `_FRONTMATTER_RE` regex + `_parse_fm` helper
- Removed function body and helpers from `main.py` (kept the import from new module)
- Updated both import sites in `app/routers/projects.py` from `app.main` to `app.storage.project_loader`

Verified: import check passes, `python start.py` starts without errors, 182/183 tests pass (1 pre-existing failure in test_db_backup unrelated to this change).
