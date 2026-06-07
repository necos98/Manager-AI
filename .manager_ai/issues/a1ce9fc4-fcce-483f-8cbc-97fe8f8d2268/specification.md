## Scope

Extract 4 duplicated code patterns in `backend/app/mcp/server.py` into shared helper functions. Pure refactor — zero behavioral changes. No new functionality. No logic changes. No API contract changes.

## The 4 Extraction Targets

### 1. `_issue_display_name(issue, max_len: int = 50) -> str`

Resolves `issue.name or (issue.description or "")[:max_len] or ""`. Replaces 11 inline occurrences.

**Constraint:** One variant at line 138 uses `[:100]`. Helper must support `max_len` parameter defaulting to 50, so callers pass `max_len=100` when needed.

**Occurrences:** 1 with max_len=100 (line 138), 6 with `[:50] or ""` (lines 144, 201, 221, 241, 261, 276), 2 with `[:50] or ""` (lines 300, 322), 2 with `[:50] or "Untitled issue"` (lines 345, 915)

### 2. `_serialize_agent(agent) -> dict`

Returns `{id, name, intent, model, allowed_tools, created_at, updated_at}`. Replaces 4 identical inline dict constructions.

**Occurrences:** create_agent (line ~972), list_agents (line ~992), get_agent (line ~1012), update_agent (line ~1041)

**Constraint:** `created_at` uses `str()` not `.isoformat()`. Preserve exact output format.

### 3. `_serialize_pipeline(pipeline) -> dict`

Returns `{id, name, steps: [{id, pipeline_id, agent_id, order_index}], created_at, updated_at}`. Replaces 6+ identical inline dict constructions.

**Occurrences:** create_pipeline (line ~1083), list_pipelines (line ~1109), get_pipeline (line ~1135), update_pipeline (line ~1162), add_step (line ~1201), reorder_steps (line ~1240)

**Constraint:** Same `str()` format for timestamps. Steps list uses `pipeline.steps or []`.

### 4. `@mcp_tool_wrapper` decorator

Handles the common pattern:
```
async with async_session() as session:
    svc = SomeService(session)
    try:
        ... do work ...
        await session.commit()
        ... emit events (optional) ...
        return result
    except AppError as e:
        return {"error": e.message}
```

Applied BELOW `@mcp.tool()`.

**Constraint:** Some tools extract data before commit (e.g., `complete_issue` at lines 137-142, `accept_issue` at line 275, `cancel_issue` at line 299, `force_finish_issue` at line 321). These need to return data from inner function, commit happens in wrapper. Inner function returns data, wrapper commits then re-returns.

**Constraint:** Tools that call `session.commit()` inside the `try` block have "before-commit" return values they extract explicitly. Wrapper must handle: inner returns `(data, needs_commit)` or similar pattern.

**Constraint:** NOT all tools use this exact pattern. Tools like `list_plugins` (line ~788), `get_plugin_config` (line ~822), `enable_plugin`/`disable_plugin` (lines ~850, ~866) have different shapes (e.g., getting project outside the try block, calling plugin_manager methods). The wrapper should only be applied where the pattern fits cleanly.

**Constraint:** Event emission stays in each tool — too varied to abstract.

## Constraints

- **Zero behavioral change.** Output dicts must be byte-identical for same inputs. No schema changes.
- **Pure extraction.** No renaming, reformatting, or restructuring beyond extracting duplicates.
- **Decorator backward-compatible.** Tools not using the decorator continue to work unchanged. Mixing decorated and non-decorated tools is fine.
- **No file splitting.** All helpers live in `mcp/server.py`. No new files.
- **Event emission NOT extracted.** Stays inline per tool.
- **All existing tests pass.** Run full `python -m pytest` after changes.

## Non-goals

- No behavioral or logic changes
- No schema or API contract changes
- No refactoring of non-duplicated code
- No new files
- No renaming/restructuring beyond extraction
- No extraction of agent/pipeline serialization for `delete_agent`, `delete_pipeline`, `remove_step` (trivial single-field returns)
- No extraction of `_file_to_dict`, `_memory_to_dict`, project link serialization, or question tools — these are single-occurrence or too varied

## Acceptance Criteria

1. `_issue_display_name(issue, max_len=50)` helper replaces all 11 inline `issue.name or (issue.description or "")[:50] or ""` expressions
2. `_serialize_agent(agent)` replaces 4 identical agent dict constructions
3. `_serialize_pipeline(pipeline)` replaces 6+ identical pipeline dict constructions
4. `@mcp_tool_wrapper` decorator reduces boilerplate for tools that fit the async-session/try-commit pattern
5. All tools that fit the session/try/except/commit pattern use the decorator
6. Tools with special patterns (extracting data before commit, plugin_manager calls) remain as-is or use partial decorator support
7. `python -m pytest` passes with no failures
8. Output format of every tool endpoint is unchanged (byte-identical for same inputs)