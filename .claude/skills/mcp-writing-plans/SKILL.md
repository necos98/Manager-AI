---
name: mcp-writing-plans
description: Use when you have an approved spec and need to write an implementation plan. MCP-native version of writing-plans - saves plan and tasks via Manager AI MCP instead of local .md files. OVERRIDES superpowers:writing-plans.
---

# MCP Writing Plans

MCP-native variant of `superpowers:writing-plans`. Same detailed planning process, but the plan and tasks are saved to Manager AI MCP — **no .md files on disk**.

**Announce at start:** "Using mcp-writing-plans to create the implementation plan via Manager AI."

**Context:** Invoked after mcp-brainstorming, with an already-approved spec and the spec's task_id available.

## Prerequisite: project_id

Read `manager.json` in the project root for the `project_id`.

## Plan structure

Before defining tasks, map out the files that will be created or modified. Each file has a clear responsibility.

- Units with well-defined interfaces, testable in isolation
- Small, focused files — if a file does too many things, split it
- Files that change together live together
- In existing codebases, follow patterns already present

## Task granularity

**Each step is an action (2-5 minutes):**
- "Write the failing test" — step
- "Run to verify it fails" — step
- "Write the minimum code to make it pass" — step
- "Verify it passes" — step
- "Commit" — step

## Process

1. **Read project_id** from `manager.json`
2. **Read the spec** — fetch from MCP with `mcp__ManagerAi__get_task_details` using the spec's task_id
3. **Verify scope** — if the spec covers multiple independent subsystems, suggest splitting into separate plans
4. **Memory scan (MUST)** — `mcp__ManagerAi__memory_search` for prior patterns, constraints, architectural decisions, and gotchas relevant to the spec. Factor findings into the plan (reuse prior conventions; flag any contradictions to the user before proceeding).
5. **Map files** — list all files to create/modify with their responsibilities
6. **Write the full plan** — task by task, step by step (see structure below)
7. **Save plan via MCP** — `mcp__ManagerAi__create_task_plan`
8. **Create MCP tasks** — one `mcp__ManagerAi__create_task` for each main task in the plan
9. **Plan review loop** — dispatch reviewer subagent; fix and re-dispatch until approved (max 3 iterations)
10. **Execution handoff** — present execution options to the user

## Task structure in the plan

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/file.py`
- Modify: `exact/path/existing.py:123-145`
- Test: `tests/exact/path/test.py`

- [ ] **Step 1: Write the failing test**
[complete test code]

- [ ] **Step 2: Run to verify it fails**
Command: `...`
Expected: FAIL with "..."

- [ ] **Step 3: Minimum implementation**
[complete code]

- [ ] **Step 4: Verify it passes**
Command: `...`
Expected: PASS

- [ ] **Step 5: Commit**
`git commit -m "feat: ..."`
```

## Saving the Plan via MCP

```
mcp__ManagerAi__create_task_plan
  project_id: <from manager.json>
  content: <full plan in markdown>
```

Then create one MCP task for each main task:

```
mcp__ManagerAi__create_task
  project_id: <from manager.json>
  name: "Task N: [Name]"
  description: <task description>
```

## Plan Review Loop

1. Dispatch subagent with: path to the MCP plan (task_id) + spec task_id
2. If ❌ issues found: fix with `mcp__ManagerAi__edit_task_plan`, re-dispatch
3. If ✅ approved: proceed to handoff

## Execution Handoff

> "Plan saved in Manager AI (task_id: `<id>`). Tasks created: N. How do you want to proceed?
>
> **1. Subagent per task** (recommended) — a fresh subagent for each task, review between tasks
> **2. Inline execution** — I execute the tasks in this session with checkpoints"

- If **Subagent** chosen: **REQUIRED SUB-SKILL:** `superpowers:subagent-driven-development`
- If **Inline** chosen: **REQUIRED SUB-SKILL:** `superpowers:executing-plans`

## Rules

- File paths always exact
- Complete code in the plan (not "add validation")
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
