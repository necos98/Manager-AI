---
name: planner
description: Easy managing planning of project tasks by using Manager_AI MCP for creating/editing/complete tasks.
---

# Planner

**This skill OVERRIDES superpowers:brainstorming, superpowers:writing-plans, and superpowers:executing-plans.**

**DO NOT write any .md files for specs or plans.**

## Two complementary tools

| Tool | Purpose |
|---|---|
| `TaskCreate` (built-in) | Track progress within the current conversation |
| Manager_AI MCP | Historicize tasks and show them visually to the user via GUI |

Use **both**:
- `TaskCreate` as normal for conversation-level task tracking
- Manager_AI MCP to create/edit/complete tasks so the user can see them in the visual interface

## What changes vs superpowers defaults

Instead of writing spec/plan to `.md` files (`docs/superpowers/specs/`, `docs/superpowers/plans/`):
- Create tasks via Manager_AI MCP — the task structure handles spec + plan together
- The MCP is the single source of truth for specs and plans (not disk files)
