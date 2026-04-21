---
name: manager-ai-memories
description: >
  Use when working inside a Manager AI project and you need long-term, cross-session
  knowledge about the project: architectural decisions, domain rules, user preferences,
  recurring patterns, gotchas, or links between concepts. Memories are project-scoped,
  hierarchical (parent/child), graph-linked, and full-text searchable via the
  `memory_*` MCP tools. Invoke this skill BEFORE answering a project-specific
  question and AFTER learning something durable the user will want available next session.
---

# Manager AI — Memories

Long-term, project-scoped notes that persist across Claude Code sessions. Backed
by the Manager AI backend (SQLite + FTS5). Accessed exclusively through MCP tools
prefixed `memory_`. Every memory belongs to exactly one `project_id`.

## Data model (what you are writing into)

- **Memory** — `{ id, project_id, title, description, parent_id, created_at, updated_at }`.
  `title` ≤ 255 chars, `description` is free-form markdown. `parent_id` builds a tree
  (cycles rejected by backend).
- **MemoryLink** — lateral edge `{ from_id → to_id, relation }` between two memories
  in the same project. `relation` is a free label (e.g. `see_also`, `contradicts`,
  `supersedes`, `implements`).
- **Search** — FTS5 over `title + description`, returns `{ memory, snippet, rank }`.

## MCP tools (authoritative list)

| Tool | Purpose |
|------|---------|
| `memory_search(project_id, query, limit=20)` | **Always try this first** before creating. FTS5 search. |
| `memory_list(project_id, parent_id=None, limit=50, offset=0)` | Browse. `parent_id=""` → root-level only. |
| `memory_get(memory_id)` / `memory_get_related(memory_id)` | Fetch one memory + parent + children + links (both directions). |
| `memory_create(project_id, title, description="", parent_id=None)` | Write a new memory. |
| `memory_update(memory_id, title=None, description=None, parent_id=None, parent_id_clear=False)` | Edit or re-parent. Pass `parent_id_clear=True` to detach. |
| `memory_delete(memory_id)` | Children are NOT cascaded — their `parent_id` is set to `NULL`. Links ARE cascaded. |
| `memory_link(from_id, to_id, relation="")` | Create lateral edge (same project only). |
| `memory_unlink(from_id, to_id, relation="")` | Remove lateral edge (must match all three). |

All writes auto-emit events (`memory_created`, `memory_updated`, `memory_deleted`,
`memory_linked`, `memory_unlinked`) consumed by the frontend sidebar — no manual
refresh needed.

## When to READ memory

Invoke `memory_search` / `memory_list` **before** answering if:

- User asks a question whose answer likely depends on past project decisions
  ("how do we handle X?", "what did we decide about Y?", "why is Z done this way?").
- You are about to make an architectural choice, pick a naming convention, or set a
  default — something the user may already have a position on.
- User says "remember", "recall", "check memory", "what do you know about…".
- You are starting a non-trivial task in an area you have not touched in this session.

Do **not** stall on memory lookups for trivia, syntax, or things clearly
derivable from the current code.

## When to WRITE memory

Save a memory when you learn something **durable and non-obvious**:

- A decision and the reason behind it ("we use SQLite because…").
- A constraint or invariant that is not enforced by the code ("vector columns must be
  stripped in tests because SQLite can't handle them").
- A user preference on how to collaborate in this project ("always run tests before
  committing in this repo").
- A recurring pattern / gotcha the user hit more than once.
- External references (dashboard URLs, ticket trackers) tied to this project.

Do **not** save:

- Anything already documented in `CLAUDE.md` or the codebase.
- Transient state (current branch, in-progress work, today's TODO).
- Info derivable from `git log` / `git blame`.
- Code snippets as memory content — link to file paths instead.

## How to structure a memory

- **title** — imperative or declarative, ≤ 80 chars ideally, uniquely searchable.
  Bad: `"notes"`. Good: `"Issue lifecycle: VALID_TRANSITIONS enforced in IssueService"`.
- **description** — markdown. Lead with the fact/rule. For decision-type memories
  include two lines: `**Why:**` and `**How to apply:**`. Cite file paths + line numbers
  where applicable (they rot — keep the *concept* primary, paths secondary).
- **parent_id** — prefer a shallow tree. Create a root "category" memory only when
  you expect ≥ 3 siblings under it. Common roots: `Architecture`, `Conventions`,
  `Known Issues`, `User Preferences`, `External References`.
- **links** — use when two memories refer to each other but are not
  parent/child. Useful relations: `see_also`, `supersedes` (newer invalidates older),
  `contradicts` (flag conflict for the user), `implements` (decision → code area).

## Workflow (canonical sequence)

1. **Before creating**: `memory_search(project_id, query=<3–5 keywords>)`.
   If a matching memory exists → `memory_update` it instead of creating a duplicate.
2. **Creating new**: decide parent. If none fits, create at root. Do not spawn a
   parent just to hold one child.
3. **Superseding**: do not delete the old memory silently. Either
   (a) update it in place with the new truth, or
   (b) create the new one and `memory_link(new, old, relation="supersedes")`, then
       edit the old memory's description to point at the new one.
4. **Contradiction**: if new info conflicts with an existing memory, surface it to
   the user before writing. Do not silently overwrite validated decisions.
5. **Verification**: a memory can be stale. If you are about to act on a memory that
   names a file/function/flag, verify it still exists (grep / read) before trusting it.

## Project scoping

Every tool call needs a `project_id` (or a `memory_id` which implies one). The
project id for the current workspace is in `manager.json` at the repo root. Never
cross project boundaries: `memory_link` rejects cross-project edges; `memory_search`
is always scoped.

## Anti-patterns

- Writing a memory mid-task "just in case" — wait until the fact is confirmed durable.
- Deep trees (> 3 levels). Prefer flat + links.
- Memories that paraphrase `CLAUDE.md`. Update `CLAUDE.md` instead.
- One memory per file. Memories are concepts, not a file index.
- Putting dates in titles ("2026-04-21 decision…"). Use `created_at` — it is already
  stored.
- Silent deletes. Prefer `supersedes` link so history is traceable.

## Quick reference

```
search   → memory_search(project_id, query, limit)
read     → memory_get(memory_id) | memory_list(project_id, parent_id)
write    → memory_create(project_id, title, description, parent_id?)
edit     → memory_update(memory_id, title?, description?, parent_id?, parent_id_clear?)
graph    → memory_link(from_id, to_id, relation) / memory_unlink(...)
remove   → memory_delete(memory_id)   # children detach, links cascade
```
