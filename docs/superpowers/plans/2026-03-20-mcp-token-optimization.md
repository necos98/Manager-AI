# MCP Token Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Minimize tokens consumed per MCP interaction by consolidating context in `server.instructions`, trimming redundant tool descriptions, and stripping large/null payloads from responses.

**Architecture:** Three layers of optimization — (1) move shared knowledge (state machine, valid values) into `server.instructions` once; (2) shorten every tool description to its essential action; (3) trim response payloads so large content (spec, plan, recap) is never echoed back and null fields are never sent.

**Tech Stack:** Python, FastMCP, pytest-asyncio (`asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio` to new tests)

---

## Optimization Summary

| Area | Problem | Fix | Est. token saving |
|---|---|---|---|
| `server.instructions` | Only mentions project_id location | Add full state machine + valid statuses | Eliminates per-description repetition |
| Tool descriptions | Repeat "Only works in X status" across 5 tools | Remove — now in instructions | ~80 tokens saved per handshake |
| `list_tasks_by_status` description | Lists all 7 status values inline | Remove — now in instructions | ~20 tokens saved |
| `get_task_details` response | Returns `project_id` (agent already knows it) | Remove field | ~10 tokens per call |
| `get_task_details` response | Sends `null` for spec/plan/recap/decline_feedback/timestamps | Omit null fields entirely | ~30 tokens per call |
| `create_task_spec` response | Echoes back the full spec the agent just wrote | Return `{id, status}` only | Up to 300+ tokens per call |
| `edit_task_spec` response | Same — echoes full spec | Return `{id, status}` only | Up to 300+ tokens per call |
| `create_task_plan` response | Echoes back full plan | Return `{id, status}` only | Up to 500+ tokens per call |
| `edit_task_plan` response | Same — echoes full plan | Return `{id, status}` only | Up to 500+ tokens per call |
| `complete_task` response | Echoes back full recap | Return `{id, status}` only | Up to 200+ tokens per call |

---

## File Map

| File | Change |
|---|---|
| `backend/app/mcp/default_settings.json` | Rewrite `server.instructions`; shorten all tool descriptions |
| `backend/app/mcp/server.py` | Trim response payloads for 5 mutation tools; strip nulls from `get_task_details` |
| `backend/tests/test_mcp_tools.py` | Add new assertions; no existing assertions need changing |
| `backend/tests/test_mcp_descriptions.py` | New file — validates instructions and descriptions |

---

## Task 1: Rewrite `server.instructions` and shorten tool descriptions

**Files:**
- Create: `backend/tests/test_mcp_descriptions.py`
- Modify: `backend/app/mcp/default_settings.json`

- [ ] **Step 1: Write the failing test**

The path must be anchored to `__file__` to be stable regardless of where pytest is invoked from:

```python
# backend/tests/test_mcp_descriptions.py
import json
from pathlib import Path

_settings_path = Path(__file__).parent.parent / "app" / "mcp" / "default_settings.json"


def test_instructions_contain_state_machine():
    data = json.loads(_settings_path.read_text(encoding="utf-8"))
    instructions = data["server.instructions"]
    for keyword in ["New", "Reasoning", "Planned", "Accepted", "Finished", "Declined", "Canceled"]:
        assert keyword in instructions, f"Missing '{keyword}' in instructions"


def test_tool_descriptions_do_not_repeat_statuses():
    data = json.loads(_settings_path.read_text(encoding="utf-8"))
    repeated_phrases = ["Only works for tasks in", "Valid values:"]
    for key, value in data.items():
        if key.startswith("tool."):
            for phrase in repeated_phrases:
                assert phrase not in value, f"'{phrase}' found in {key} — move to instructions"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_mcp_descriptions.py -v
```
Expected: FAIL — current descriptions contain "Only works for tasks in" and "Valid values:"

- [ ] **Step 3: Rewrite `default_settings.json`**

Replace the full content of `backend/app/mcp/default_settings.json`:

```json
{
  "server.name": "Manager AI",
  "server.instructions": "Manager AI manages tasks and projects. Always read project_id from manager_ai.json in the root of the project you are working on.\n\nTask lifecycle (in order): New → Reasoning → Planned → Accepted → Finished\nSide exits from any status: Declined, Canceled.\n\nValid status values: New, Reasoning, Planned, Accepted, Declined, Finished, Canceled.",

  "tool.get_task_details.description": "Get full details of a task: id, name, description, status, priority. Non-null fields also included: specification, plan, recap, decline_feedback, created_at, updated_at.",
  "tool.get_task_status.description": "Get the current status of a task.",
  "tool.get_project_context.description": "Get project info: name, path, description, tech_stack.",
  "tool.set_task_name.description": "Set the name of a task.",
  "tool.complete_task.description": "Save recap and move task to Finished. Requires Accepted status.",
  "tool.create_task_spec.description": "Save specification and move task to Reasoning. Requires New or Declined status.",
  "tool.edit_task_spec.description": "Update the specification. Requires Reasoning status. Does not change status.",
  "tool.create_task_plan.description": "Save implementation plan and move task to Planned. Requires Reasoning status.",
  "tool.edit_task_plan.description": "Update the implementation plan. Requires Planned status. Does not change status.",
  "tool.accept_task.description": "Move task to Accepted. Requires Planned status. Call after user confirms plan.",
  "tool.cancel_task.description": "Move task to Canceled. Works from any status.",
  "tool.create_task.description": "Create a new task. Returns id, name, description, status, priority.",
  "tool.list_tasks_by_status.description": "List tasks in a project, optionally filtered by status. Returns id, name, description, status, priority ordered by priority then creation date."
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_mcp_descriptions.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/mcp/default_settings.json backend/tests/test_mcp_descriptions.py
git commit -m "feat: consolidate MCP state machine into instructions, shorten tool descriptions"
```

---

## Task 2: Strip echoed content from mutation responses

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/tests/test_mcp_tools.py`

The 5 tools that echo back large content the agent just wrote:
- `create_task_spec` — remove `specification` from response
- `edit_task_spec` — remove `specification` from response
- `create_task_plan` — remove `plan` from response
- `edit_task_plan` — remove `plan` from response
- `complete_task` — remove `recap` from response

Note: `asyncio_mode = "auto"` is set in `pyproject.toml` — do NOT add `@pytest.mark.asyncio`.

- [ ] **Step 1: Write failing tests for all 5 tools**

Append to `backend/tests/test_mcp_tools.py`:

```python
async def test_create_task_spec_does_not_echo_spec(db_session, project):
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="T", priority=1)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.create_task_spec(str(project.id), str(task.id), "# Spec")

    assert "specification" not in result
    assert result["status"] == "Reasoning"
    assert "id" in result


async def test_edit_task_spec_does_not_echo_spec(db_session, project):
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="T", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec v1")

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.edit_task_spec(str(project.id), str(task.id), "# Spec v2")

    assert "specification" not in result
    assert result["status"] == "Reasoning"


async def test_create_task_plan_does_not_echo_plan(db_session, project):
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="T", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.create_task_plan(str(project.id), str(task.id), "# Plan")

    assert "plan" not in result
    assert result["status"] == "Planned"


async def test_edit_task_plan_does_not_echo_plan(db_session, project):
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="T", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")
    await task_service.create_plan(task.id, project.id, "# Plan v1")

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.edit_task_plan(str(project.id), str(task.id), "# Plan v2")

    assert "plan" not in result
    assert result["status"] == "Planned"


async def test_complete_task_does_not_echo_recap(db_session, project):
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="T", priority=1)
    await task_service.create_spec(task.id, project.id, "# Spec")
    await task_service.create_plan(task.id, project.id, "# Plan")
    await task_service.accept_task(task.id, project.id)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.complete_task(str(project.id), str(task.id), "Done.")

    assert "recap" not in result
    assert result["status"] == "Finished"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py -k "does_not_echo" -v
```
Expected: all 5 FAIL

- [ ] **Step 3: Update the 5 mutation tool responses in `server.py`**

In `backend/app/mcp/server.py`, apply these changes:

```python
# complete_task — line ~135
# was: return {"id": task.id, "status": task.status.value, "recap": task.recap}
return {"id": task.id, "status": task.status.value}

# create_task_spec — line ~148
# was: return {"id": task.id, "status": task.status.value, "specification": task.specification}
return {"id": task.id, "status": task.status.value}

# edit_task_spec — line ~161
# was: return {"id": task.id, "status": task.status.value, "specification": task.specification}
return {"id": task.id, "status": task.status.value}

# create_task_plan — line ~174
# was: return {"id": task.id, "status": task.status.value, "plan": task.plan}
return {"id": task.id, "status": task.status.value}

# edit_task_plan — line ~187
# was: return {"id": task.id, "status": task.status.value, "plan": task.plan}
return {"id": task.id, "status": task.status.value}
```

- [ ] **Step 4: Run new tests to verify they all pass**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py -k "does_not_echo" -v
```
Expected: all 5 PASS

- [ ] **Step 5: Run full test suite to catch regressions**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_tools.py
git commit -m "perf: strip echoed content from MCP mutation responses to save tokens"
```

---

## Task 3: Strip null fields from `get_task_details` response

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/tests/test_mcp_tools.py`

A new task currently sends: `"specification": null, "plan": null, "recap": null, "decline_feedback": null, "project_id": "...", "created_at": null, "updated_at": null`. All of this is noise. Optional fields should only appear when they have a value.

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_mcp_tools.py`:

```python
async def test_get_task_details_omits_null_fields(db_session, project):
    """A new task should not include null optional fields in the response."""
    task_service = TaskService(db_session)
    task = await task_service.create(project_id=project.id, description="New task", priority=2)
    await db_session.refresh(task)  # populate server_default timestamps

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_task_details(str(project.id), str(task.id))

    # Optional fields must be absent when null — not sent as null
    for field in ("specification", "plan", "recap", "decline_feedback", "project_id"):
        assert field not in result, f"'{field}' should be omitted when null/redundant"

    # Always-present fields
    assert "id" in result
    assert "status" in result
    assert "priority" in result
    assert "created_at" in result   # populated after refresh
    assert "updated_at" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_get_task_details_omits_null_fields -v
```
Expected: FAIL

- [ ] **Step 3: Rewrite `get_task_details` return block in `server.py`**

Replace the `return { ... }` block inside `get_task_details` with:

```python
result = {
    "id": task.id,
    "name": task.name,
    "description": task.description,
    "status": task.status.value,
    "priority": task.priority,
}
# Omit timestamps when null (unrefreshed rows) — include when populated
if task.created_at:
    result["created_at"] = task.created_at.isoformat()
if task.updated_at:
    result["updated_at"] = task.updated_at.isoformat()
# Omit optional content fields when null
for field in ("specification", "plan", "recap", "decline_feedback"):
    value = getattr(task, field)
    if value is not None:
        result[field] = value
return result
```

- [ ] **Step 4: Run new test to verify it passes**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_get_task_details_omits_null_fields -v
```
Expected: PASS

- [ ] **Step 5: Verify existing `get_task_details` test still passes**

The existing test sets a spec before calling the tool, so `specification` will be present.

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_mcp_get_task_details_includes_specification -v
```
Expected: PASS

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/server.py backend/tests/test_mcp_tools.py
git commit -m "perf: omit null and redundant fields from get_task_details response"
```
