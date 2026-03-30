---
name: mcp-brainstorming
description: Use when starting any new feature, component, or design work. MCP-native version of brainstorming - saves spec via Manager AI MCP instead of local .md files. OVERRIDES superpowers:brainstorming.
---

# MCP Brainstorming

MCP-native variant of `superpowers:brainstorming`. Same collaborative exploration process, but the spec is saved via Manager AI MCP — **no .md files on disk**.

**Announce at start:** "Using mcp-brainstorming to explore the design and create the spec via Manager AI."

<HARD-GATE>
DO NOT write code, scaffold, or invoke implementation skills before presenting the design and receiving user approval.
</HARD-GATE>

## Prerequisite: project_id

Read `manager.json` in the project root for the `project_id` required by all MCP tools.

## Checklist

Create a task for each item and complete them in order:

1. **Read project_id** from `manager.json`
2. **Explore project context** — files, structure, recent commits; use `mcp__ManagerAi__get_project_context`
3. **Ask clarifying questions** — one at a time; scope, constraints, success criteria
4. **Propose 2-3 approaches** — with trade-offs and a recommendation
5. **Present the design** — section by section, ask for approval after each section
6. **Save spec via MCP** — `mcp__ManagerAi__create_task_spec`
7. **Spec review loop** — dispatch reviewer subagent; fix and re-dispatch until approved (max 3 iterations)
8. **Request user review** — share the spec task_id, wait for approval
9. **Transition to mcp-writing-plans** — invoke the skill for the plan

## Flow

```dot
digraph mcp_brainstorming {
    "Read project_id" [shape=box];
    "Explore context" [shape=box];
    "Clarifying questions" [shape=box];
    "Propose 2-3 approaches" [shape=box];
    "Present design" [shape=box];
    "User approves?" [shape=diamond];
    "Save spec via MCP" [shape=box];
    "Review loop" [shape=box];
    "Spec approved?" [shape=diamond];
    "User revises?" [shape=diamond];
    "Invoke mcp-writing-plans" [shape=doublecircle];

    "Read project_id" -> "Explore context";
    "Explore context" -> "Clarifying questions";
    "Clarifying questions" -> "Propose 2-3 approaches";
    "Propose 2-3 approaches" -> "Present design";
    "Present design" -> "User approves?";
    "User approves?" -> "Present design" [label="no, revise"];
    "User approves?" -> "Save spec via MCP" [label="yes"];
    "Save spec via MCP" -> "Review loop";
    "Review loop" -> "Spec approved?";
    "Spec approved?" -> "Review loop" [label="issues"];
    "Spec approved?" -> "User revises?" [label="ok"];
    "User revises?" -> "Save spec via MCP" [label="changes"];
    "User revises?" -> "Invoke mcp-writing-plans" [label="approved"];
}
```

## Saving the Spec

```
mcp__ManagerAi__create_task_spec
  project_id: <from manager.json>
  content: <full spec in markdown>
```

After saving:
> "Spec saved in Manager AI (task_id: `<id>`). Review it in the interface and let me know if you want changes before moving to the plan."

## Principles

- **One question at a time**
- **Prefer multiple choice**
- **YAGNI** — remove unnecessary features
- **Always explore 2-3 approaches**
- **Incremental validation** — present, get approval, then advance
