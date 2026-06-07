## Implementation Plan: Refactor mcp/server.py — Extract Duplicated Patterns

**File:** `backend/app/mcp/server.py` (1415 lines, currently 4 duplicated patterns)

**Strategy:** Pure extraction, zero behavioral changes. Each extraction is independent but order matters: add helpers first, then apply them. Run `python -m pytest` after each extraction target to verify.

---

### Step 1: Add `import functools` (line 1, after existing imports)

Insert `import functools` in the import block after line 4 (`from pathlib import Path`). Needed for the decorator wrapper.

---

### Step 2: Add 4 helper definitions (insert after line 29, before first `@mcp.tool`)

Insert these between `logger = logging.getLogger(__name__)` and the first `@mcp.tool` decorator:

```python
def _issue_display_name(issue, max_len: int = 50) -> str:
    return issue.name or (issue.description or "")[:max_len] or ""


def _serialize_agent(agent) -> dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "intent": agent.intent,
        "model": agent.model,
        "allowed_tools": agent.allowed_tools,
        "created_at": str(agent.created_at) if agent.created_at else None,
        "updated_at": str(agent.updated_at) if agent.updated_at else None,
    }


def _serialize_pipeline(pipeline) -> dict:
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "steps": [
            {
                "id": s.id,
                "pipeline_id": s.pipeline_id,
                "agent_id": s.agent_id,
                "order_index": s.order_index,
            }
            for s in (pipeline.steps or [])
        ],
        "created_at": str(pipeline.created_at) if pipeline.created_at else None,
        "updated_at": str(pipeline.updated_at) if pipeline.updated_at else None,
    }


def mcp_tool_wrapper(func):
    """Wraps async with async_session() + try/except AppError."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            try:
                return await func(session, *args, **kwargs)
            except AppError as e:
                return {"error": e.message}
    return wrapper
```

**Constraint:** Decorator wraps ONLY session creation + AppError handling. Service instantiation, commit(), and event emission stay inside each tool — too varied to abstract. Tools with before-commit data extraction (complete_issue, accept_issue, cancel_issue, force_finish_issue) call commit() inside their body; decorator remains unaware.

---

### Step 3: Apply `_issue_display_name` — 11 replacements, 1 file

Replace each occurrence of `issue.name or (issue.description or "")[:N] or ""` (or similar) with `_issue_display_name(issue, max_len=N)`:

| # | Line (current) | Expression | Replacement |
|---|---|---|---|
| 1 | 138 | `issue.name or (issue.description or "")[:100]` | `_issue_display_name(issue, max_len=100)` (note: no trailing `or ""` because this uses different grouping — the original lacks the trailing fallback) |
| 2 | 144 | `issue.name or (issue.description or "")[:50] or ""` | `_issue_display_name(issue)` |
| 3 | 201 | same | `_issue_display_name(issue)` |
| 4 | 221 | same | `_issue_display_name(issue)` |
| 5 | 241 | same | `_issue_display_name(issue)` |
| 6 | 261 | same | `_issue_display_name(issue)` |
| 7 | 276 | same | `_issue_display_name(issue)` |
| 8 | 300 | same | `_issue_display_name(issue)` |
| 9 | 322 | same | `_issue_display_name(issue)` |
| 10 | 345 | `issue.name or (issue.description or "")[:50] or "Untitled issue"` | `_issue_display_name(issue) or "Untitled issue"` |
| 11 | 915 | same | `_issue_display_name(issue) or "Untitled issue"` |

**Verify:** `_issue_display_name(issue)` returns `""` when name and desc are both empty. So `_issue_display_name(issue) or "Untitled issue"` preserves the fallback behavior exactly.

**Important:** Line 138 has a quirk — `issue.name or (issue.description or "")[:100]` (no trailing `or ""`). This means if both name and desc are empty/falsy, the expression returns `""` (from the slice of empty string). `_issue_display_name(issue, max_len=100)` returns the same. Verified correct.

---

### Step 4: Apply `_serialize_agent` — 4 replacements

Replace inline dict constructions in these tools:
1. **create_agent** (lines 972-980): replace the dict in the `return` inside `try`
2. **list_agents** (lines 992-1001): replace the dict inside the list comprehension
3. **get_agent** (lines 1012-1020): replace the dict in the `return` inside `try`
4. **update_agent** (lines 1041-1049): replace the dict in the `return` inside `try`

Each replacement is `_serialize_agent(agent)` / `_serialize_agent(a)` as appropriate.

**Constraint:** `str()` format for timestamps is preserved — `_serialize_agent` uses `str(agent.created_at)` (not `.isoformat()`). Byte-identical output.

---

### Step 5: Apply `_serialize_pipeline` — 6 replacements

Replace inline dict constructions in these tools:
1. **create_pipeline** (lines 1083-1097): replace the dict after `await svc.get_pipeline(pipeline.id)`
2. **list_pipelines** (lines 1109-1123): replace dict inside list comprehension
3. **get_pipeline** (lines 1135-1149): replace the dict in `try` return
4. **update_pipeline** (lines 1162-1176): replace the dict after `await svc.get_pipeline(pipeline_id)`
5. **add_step** (lines 1201-1215): replace dict after `await svc.get_pipeline(pipeline_id)`
6. **reorder_steps** (lines 1240-1254): replace dict after `await svc.get_pipeline(pipeline_id)`

Each replacement is `_serialize_pipeline(pipeline)` or `_serialize_pipeline(p)`.

---

### Step 6: Apply `@mcp_tool_wrapper` — tools that fit the session/try/commit pattern

**Candidate tools (23):** Most issue-service, project-service, agent, and pipeline tools follow: `async with async_session() -> try/except AppError -> work -> commit -> events -> return`. The decorator handles session + try/except; the inner function receives `session` as first param.

#### Step 6a: Read-only tools (no commit, no events) — 5 tools
- `get_issue_details` (lines 33-56): Remove `async with async_session() as session:` + `try/except`. Add `@mcp_tool_wrapper`. Function signature becomes `(session, project_id, issue_id)`. Body: `issue_service = IssueService(session)` then the rest minus indentation and except clause.
- `get_issue_status` (lines 60-67): Same pattern. Body: `issue_service = IssueService(session)`, `issue = await issue_service.get_for_project(...)`, return `{"id": ...}`.
- `get_project_context` (lines 71-84): Same pattern.
- `get_agent` (lines 1007-1022): Same pattern.
- `get_pipeline` (lines 1130-1151): Same pattern.

#### Step 6b: Write tools (commit + events) — 10 tools
- `update_project_context` (lines 88-107): `svc = ProjectService(session)`, `project = await svc.update(...)`, `commit()`, events, `return _serialize_pipeline(...)` → actually return is `{id, name, path, description, tech_stack}` — no serializer applies.
- `set_issue_name` (lines 111-127): `svc = IssueService(session)`, `issue = await svc.set_name(...)`, `commit()`, events, `return {...}`.
- `create_issue_spec` (lines 190-206): Same pattern.
- `edit_issue_spec` (lines 210-226): Same pattern.
- `create_issue_plan` (lines 230-246): Same pattern.
- `edit_issue_plan` (lines 250-265): Same pattern.
- `create_agent` (lines 961-982): `svc = AgentService(session)`, `agent = await svc.create(...)`, `commit()`, `return _serialize_agent(agent)`.
- `update_agent` (lines 1026-1051): `svc = AgentService(session)`, `agent = await svc.update(...)`, `commit()`, `return _serialize_agent(agent)`.
- `create_pipeline` (lines 1070-1099): Complex (multi-step), but still follows session/try/commit. Returns `_serialize_pipeline(pipeline)`.
- `update_pipeline` (lines 1155-1178): `await svc.update_pipeline(...)`, `commit()`, `pipeline = await svc.get_pipeline(...)`, `return _serialize_pipeline(pipeline)`.

#### Step 6c: Before-commit extraction pattern — 4 tools
When the decorator catches exceptions from `await func(session, ...)`, the commit() must happen INSIDE func (before the decorator returns). These tools extract data before commit — the inner function calls commit() explicitly, then emits events, then returns.

- `complete_issue` (lines 131-159): Inner: issue_service → complete → extract data → commit() → events → return.
- `accept_issue` (lines 270-290): Inner: issue_service → accept → extract → commit() → events → return.
- `cancel_issue` (lines 294-312): Inner: issue_service → cancel → extract → commit() → events → return.
- `force_finish_issue` (lines 316-334): Inner: issue_service → force_finish → extract → commit() → events → return.

**Important:** These tools MUST call `await session.commit()` inside the inner function, BEFORE raising any exception after commit. If commit itself raises `AppError`, the decorator catches it. This is safe because commit() is the last operation before returns that don't raise.

#### Step 6d: Additional tools — 4 tools
- `add_step` (lines 1194-1217): `await svc.add_step(...)`, `commit()`, `pipeline = await svc.get_pipeline(...)`, `return _serialize_pipeline(pipeline)`.
- `reorder_steps` (lines 1233-1256): Same pattern as add_step.
- `delete_agent` (lines 1055-1063): `svc = AgentService(session)`, `await svc.delete(...)`, `commit()`, `return {"deleted": True}`.
- `delete_pipeline` (lines 1182-1190): `svc = PipelineService(session)`, `await svc.delete_pipeline(...)`, `commit()`, `return {"deleted": True}`.

---

### Step 7: Tools NOT to decorate — keep as-is

These tools have shapes that don't fit the decorator pattern:

| Tool | Reason |
|------|--------|
| `create_issue` (line 163) | Pre-session validation (empty description, priority range) |
| `send_notification` (line 338) | No commit, no try/except |
| `get_next_issue` (line 531) | Has before-session SettingsService check |
| `create_plan_tasks` (line 365) | Complex return with events list comprehension |
| `replace_plan_tasks` (line 385) | Same as create_plan_tasks |
| `update_task_status` (line 405) | Complex: loops projects, fires hooks, multiple services |
| `update_task_name` (line 462) | Complex: loops projects to find issue |
| `delete_task` (line 493) | Complex: finds owning issue before deletion |
| `get_plan_tasks` (line 523) | No try/except AppError at all |
| `list_agents` (line 986) | No try/except |
| `list_pipelines` (line 1103) | No try/except |
| `remove_step` (line 1221) | Minimal — just delete + commit |
| `list_project_files` (line 664) | No try/except |
| `read_project_file` (line 672) | Manual None check, not AppError |
| `get_project_links` (line 706) | No try/except |
| All project link tools | Single occurrence, no duplication |
| All memory tools (lines 565-638) | Error handling + events outside try block, unusual shapes |
| All plugin tools (lines 788-875) | Session used only for project lookup, plugin_manager calls outside session |
| All credential tools (lines 746-780) | Mixed patterns — some no try/except, set_credential has no try/except |
| `run_pipeline` (line 1263) | Complex validation |
| `get_pipeline_run_status` (line 1284) | Returns svc result directly |
| `get_active_agent` (line 1294) | Returns dict with active check |
| `get_active_pipeline_run` (line 1318) | Same as above |
| `send_agent_message` (line 1329) | Same as above |
| `get_pipeline_messages` (line 1345) | Returns messages directly |
| `finished_pipeline_step` (line 1352) | Complex logic, rejection handling |
| `delete_credential` (line 773) | Minimal — delete + commit + return |
| `ask_user_question` (line 884) | Complex flow with question_store |

---

### Verification

Run after each step:
```bash
cd backend && python -m pytest
```

All tests must pass with zero failures. The refactor is pure extraction — any test failure means a behavioral change was introduced.

### Summary of changes

| Target | Files changed | Lines added | Lines removed | Net change |
|--------|--------------|-------------|---------------|------------|
| `_issue_display_name` | 1 | ~5 | ~55 | ~−50 |
| `_serialize_agent` | 1 | ~10 | ~48 | ~−38 |
| `_serialize_pipeline` | 1 | ~14 | ~72 | ~−58 |
| `@mcp_tool_wrapper` | 1 | ~12 (wrapper) + ~0 (tools, mostly indent) | ~92 (session/try/except per tool) | ~−80 |
| **Total** | **1** | **~41** | **~267** | **~−226** |

Indentation changes for decorated tools aren't counted in lines — they simply remove 2 indent levels (session + try).
