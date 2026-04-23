---
name: mcp-search-project-context
description: Use when you need to find relevant past issues, decisions, or knowledge stored in the Manager AI project. Triggers on questions like "what did we do for X", "find related issues", "search project history", or when building on prior work.
---

# MCP Search Project Context

Manager AI's project history lives on disk under each project's
`.manager_ai/` folder — not in a vector/FTS index. You search it with
plain filesystem tools (Grep, Read), the same way you'd search any
codebase.

## Prerequisite

Read `manager.json` at the repo root for the `project_id`; the project's
`path` comes from `mcp__ManagerAi__get_project_context(project_id)` when
you need it.

## Where the history lives

```
<project.path>/.manager_ai/
├── issues.yaml                    # index: every issue id + light metadata
├── issues/<id>/
│   ├── issue.yaml                 # status, priority, tasks, relations
│   ├── description.md
│   ├── specification.md           # present from Reasoning onward
│   ├── plan.md                    # present from Planned onward
│   ├── recap.md                   # present when Finished — the "what we did + why"
│   └── feedback/<fb-id>.md
├── memories.yaml                  # index of long-term memories (see manager-ai-memories skill)
└── memories/<id>.md
```

Completed issues carry their full story in `recap.md`. Memories carry
durable decisions. Both are plain markdown — grep them.

## Typical flow

1. **Memories first** (`manager-ai-memories` skill): decisions and gotchas
   are stored there deliberately, without the noise of full issue bodies.
   `Grep -ri "<3–5 keywords>" .manager_ai/memories/`.
2. **Recaps next**: `Grep -ri "<keyword>" .manager_ai/issues/*/recap.md`
   to find finished issues that touched the area.
3. **Specs / plans if still hunting**:
   `Grep -ri "<keyword>" .manager_ai/issues/*/specification.md .manager_ai/issues/*/plan.md`.
4. **Fetch the full story**: once a hit looks relevant,
   `Read .manager_ai/issues/<id>/recap.md` (or `specification.md` /
   `plan.md`) for context. Issue metadata lives in `issues/<id>/issue.yaml`.

If `issues.yaml` / `memories.yaml` is missing or stale, the backend may
be off — fall back to raw `Grep` on the `.md` files; they are the source
of truth.

## Query tips

- Grep multiple keyword combinations before giving up. Phrases beat
  single words: `"token refresh"` not `"token"`.
- Use `-l` to scan file-by-file then `Read` the best match.
- If a memory references an issue id, jump straight to
  `.manager_ai/issues/<id>/recap.md`.

## When the answer isn't there

- Issue may still be in progress (`status != Finished`): check
  `issues.yaml` entries whose `status` is `New` / `Reasoning` / `Planned`
  / `Accepted`.
- Feature may be documented in `CLAUDE.md` rather than a memory/issue —
  check that first for repo-wide conventions.
- If still nothing, tell the user the history is silent on the topic
  instead of guessing.

## Anti-patterns

- Using `memory_search` / `search_project_files` — **those MCP tools no
  longer exist**. Grep the filesystem directly.
- Inventing a chunk id or a file id. IDs come from `issues.yaml` /
  `memories.yaml`.
- Reading every issue's `specification.md` in full when a recap or
  memory already answers the question.

## Quick reference

```
# Memories
Grep -ri "<keyword>" .manager_ai/memories/
Read .manager_ai/memories.yaml

# Finished-issue recaps
Grep -ri "<keyword>" .manager_ai/issues/*/recap.md

# Full issue metadata
Read .manager_ai/issues/<id>/issue.yaml
Read .manager_ai/issues/<id>/specification.md
Read .manager_ai/issues/<id>/plan.md
Read .manager_ai/issues/<id>/recap.md
```
