## Implementation Plan: Extract `_load_project_into_memory` into `storage/project_loader.py`

### Overview

Extract the 170-line `_load_project_into_memory` function (main.py:118-288) and its 5 module-level helpers (main.py:291-331) into a new standalone module `backend/app/storage/project_loader.py`. Update import references in **2 call sites** across `main.py` and `projects.py`.

---

### Step 1 — Create `backend/app/storage/project_loader.py`

New module with 3 sections:

**Section A — Module-level boilerplate:**
```python
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)
```

**Section B — Module-level helpers moved verbatim (main.py:293-331):**
- `_read_optional_md(_atomic, _paths, project_path, issue_id, field_name) -> str | None`
- `_opt_str_static(value: Any) -> str | None`
- `_as_iso(value: Any) -> str`
- `_task_from_dict(d: dict) -> Any` — keeps its local `from app.storage.issue_store import TaskRecord` inside
- `_relation_from_dict(d: dict) -> Any` — keeps its local `from app.storage.issue_store import RelationRecord` inside

**Section C — `_load_project_into_memory` function (moved from main.py:118-288):**
- Same function signature: `def _load_project_into_memory(project_path: str, store: Any) -> None:`
- `_FRONTMATTER_RE` compiled once at module level (before function def), not inside the function body
- `_parse_fm(text: str) -> dict[str, Any]` promoted to module-level (before function def), takes `_FRONTMATTER_RE` via closure
- Nested closures `_opt_str`, `_as_str`, `_link_from_dict` promoted to module-level (before function def, or inside as before — either works; spec doesn't mandate which)
- All local imports preserved inside function body: `from app.storage import atomic as _atomic, paths as _paths` and `from app.storage.memory_store import MemoryRecord, MemoryLinkRecord`, `from app.storage.issue_store import IssueRecord, TaskRecord, RelationRecord`, `from app.storage.file_store import FileRecord`, `import yaml as _yaml` (inside `_parse_fm`)
- `import re as _re` kept inside function body (per spec, redundant but harmless since module-level `re` exists)
- 6 `logger.warning/info` calls now resolve to new module's `logger`

**What `_FRONTMATTER_RE` looks like at module level:**
```python
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
```

**What `_parse_fm` looks like at module level:**
```python
def _parse_fm(text: str) -> dict[str, Any]:
    if not text:
        return {"meta": {}, "body": ""}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {"meta": {}, "body": text}
    import yaml as _yaml
    meta = _yaml.safe_load(m.group(1)) or {}
    return {"meta": meta, "body": m.group(2)}
```

---

### Step 2 — Remove from `main.py`

**Delete** main.py:118-331 (the `_load_project_into_memory` function + 5 module-level helpers).

**Add** import at top of main.py (after line 38, before `logger`):
```python
from app.storage.project_loader import _load_project_into_memory
```

---

### Step 3 — Update `projects.py` imports

**Change both import sites** (lines 343 and 421):
- `from app.main import _load_project_into_memory` → `from app.storage.project_loader import _load_project_into_memory`

---

### Step 4 — Verify

1. **Import check**: `python -c "from app.storage.project_loader import _load_project_into_memory"` — must succeed
2. **Startup**: `python start.py` — must load projects without errors
3. **Callers**: `_load_project_into_memory` referenced in main.py `_startup_load_projects` (line 408) and projects.py lines 344, 423 — all must resolve correctly
4. **Lint**: `cd frontend && npm run lint` — no regressions

---

### Files changed

| File | Action |
|------|--------|
| `backend/app/storage/project_loader.py` | **Create** — new module |
| `backend/app/main.py` | **Delete** lines 118-331, **add** 1 import |
| `backend/app/routers/projects.py` | **Change** 2 imports |

### Risk notes

- **Circular imports**: None expected — all store imports stay local inside function body, same as current pattern
- **Logger**: New module has its own logger, existing `logger` calls just rebind naturally
- **`_FRONTMATTER_RE`**: Moving to module level changes it from per-call recompile to once at import time — safe, pure perf improvement
- **No behavioral change**: Function signature, return value, and all side effects identical
