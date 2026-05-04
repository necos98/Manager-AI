# Implementation Plan: Resource Consistency Health Check

**Goal:** Add `_check_resource_consistency()` to the existing health endpoint that scans all `.manager_ai/` YAML files for `project_id` mismatches and auto-fixes them.

**Architecture:** Single new function in `projects.py` router. Reads `manager.json` for authoritative ID, iterates over 4 resource types (issues.yaml, individual issue files, memories.yaml, memory .md frontmatter), compares `project_id`, rewrites mismatches using `yaml.safe_dump` + `os.replace`. No new files or services needed.

**Tech Stack:** Python, PyYAML, FastAPI

---

## Resource types to scan

1. **`issues.yaml`** — top-level `issues` list, each entry has `project_id`
2. **`.manager_ai/issues/<id>/issue.yaml`** — individual file, top-level `project_id`
3. **`memories.yaml`** — top-level `memories` list, each entry has `project_id`
4. **`.manager_ai/memories/<id>.md`** — YAML frontmatter between `---` delimiters, `project_id` field

## Algorithm

```
_check_resource_consistency(project):
    1. Read manager.json → auth_id
       If missing → return { ok: null, scanned: 0, fixed: 0, details: [], note: "manager.json missing" }
    2. Initialize scanned=0, fixed=0, details=[]
    3. Scan issues.yaml → for each entry with mismatched project_id → fix
    4. Scan issues/<id>/issue.yaml files → for each with mismatched project_id → fix
    5. Scan memories.yaml → for each entry with mismatched project_id → fix
    6. Scan memories/<id>.md files → parse frontmatter, fix mismatched project_id
    7. Return { ok: fixed==0, scanned, fixed, details }
```

## YAML handling

- **issues.yaml / memories.yaml**: Load as dict, iterate `issues`/`memories` list, update `project_id`, dump back with `yaml.safe_dump(sort_keys=False, allow_unicode=True, width=4096)`
- **issue.yaml**: Load, update `project_id`, dump back
- **memory .md**: Split on `---`, parse first YAML block, update `project_id`, dump, reassemble with `---`
- **Atomic write**: Write to `<path>.tmp`, `os.replace(tmp, path)` — same pattern as `storage/atomic.py`
