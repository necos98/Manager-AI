---
name: manager-ai-memories
description: >
  Use when working inside a Manager AI project and you need long-term, cross-session
  knowledge about the project: architectural decisions, domain rules, user preferences,
  recurring patterns, gotchas, or links between concepts. Memories are project-scoped,
  hierarchical (parent/child), graph-linked. Read them with Grep/Read on
  `.manager_ai/memories/`; write them through the `memory_*` MCP tools.
  Invoke this skill BEFORE answering a project-specific question and AFTER learning
  something durable the user will want available next session.
---

<EXTREMELY-IMPORTANT>
Before answering ANY project-specific question, before making ANY
architectural choice, and after learning ANY durable fact, you MUST
consult memory. Not optional. Not "if it seems relevant."

**Read triggers — scan `.manager_ai/memories/` before responding when:**
- user asks "how do we…", "what did we decide…", "why is X done this way"
- you are about to choose a naming convention, default, or architecture
- you are starting a non-trivial task in an area not touched this session
- user says "remember", "recall", "check memory"

**Write triggers — call `memory_create` (or `memory_update`) when:**
- an issue completes and its recap names a durable decision, constraint, gotcha, or preference
- the user states a preference that will apply to future work
- you hit a non-obvious gotcha you would want future-you to know

If unsure whether to consult memory, do it. Cost of a spurious Grep is tiny; cost of missing a prior decision is high.
</EXTREMELY-IMPORTANT>

# Manager AI — Memories

Long-term, project-scoped notes that persist across Claude Code sessions. Storage
is file-based, per project, under `<project.path>/.manager_ai/`:

```
.manager_ai/
├── memories.yaml          # rollup index: id, title, parent_id, created_at, links
└── memories/
    └── <memory-id>.md     # frontmatter (id, title, parent_id, links, ts) + body
```

`memories.yaml` is a derived index — the `.md` files are source of truth.
If a backend is running, it rebuilds the index on every write; otherwise the
watcher does so when files change externally.

## Data model

- **Memory** — `{ id, project_id, title, description, parent_id, created_at, updated_at, links[] }`.
  `title` ≤ 255 chars, `description` is free-form markdown (the body of the `.md`).
  `parent_id` builds a tree (cycles rejected by backend).
- **Link** — lateral edge `{ to_id, relation }` stored in the source memory's frontmatter.
  `relation` is a free label (e.g. `see_also`, `contradicts`, `supersedes`, `implements`).

## How to READ

Use plain filesystem tools. No MCP read tools — read the files directly.

- **Enumerate all memories**: `Read .manager_ai/memories.yaml` — each entry has id, title, parent_id, links.
- **Keyword search**: `Grep -r "<term>" .manager_ai/memories/` (case-insensitive). Grep matches both frontmatter and body.
- **Fetch one**: `Read .manager_ai/memories/<id>.md` — full frontmatter + body.
- **Find children of a parent**: scan `memories.yaml` for entries whose `parent_id` equals the target.
- **Find inbound links**: scan `memories.yaml` for entries whose `links[].to_id` equals the target.

Invoke these BEFORE answering if:

- User asks a question whose answer likely depends on past project decisions.
- You are about to make an architectural choice, pick a naming convention, or set a default.
- User says "remember", "recall", "check memory", "what do you know about…".
- You are starting a non-trivial task in an area you have not touched this session.

Do **not** stall on memory lookups for trivia, syntax, or things clearly derivable from the current code.

## How to WRITE

Always through the MCP tools — the backend owns validation (cycle rejection,
cross-project link guard) and emits realtime events to the frontend.

| Tool | Purpose |
|------|---------|
| `memory_create(project_id, title, description="", parent_id=None)` | Write a new memory. |
| `memory_update(memory_id, title=None, description=None, parent_id=None, parent_id_clear=False)` | Edit or re-parent. Pass `parent_id_clear=True` to detach. |
| `memory_delete(memory_id)` | Children are detached (`parent_id` → `NULL`); inbound links are cascaded. |
| `memory_link(from_id, to_id, relation="")` | Create lateral edge (same project only). |
| `memory_unlink(from_id, to_id, relation="")` | Remove lateral edge (must match all three). |

Write a memory when you learn something **durable and non-obvious**:

- A decision and the reason behind it ("we use SQLite because…").
- A constraint or invariant not enforced by the code.
- A user preference on how to collaborate in this project.
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
- **description** (the `.md` body) — markdown. Lead with the fact/rule. For
  decision-type memories include two lines: `**Why:**` and `**How to apply:**`.
  Cite file paths + line numbers where applicable (they rot — keep the *concept*
  primary, paths secondary).
- **parent_id** — prefer a shallow tree. Create a root "category" memory only when
  you expect ≥ 3 siblings under it. Common roots: `Architecture`, `Conventions`,
  `Known Issues`, `User Preferences`, `External References`.
- **links** — use when two memories refer to each other but are not
  parent/child. Useful relations: `see_also`, `supersedes` (newer invalidates older),
  `contradicts` (flag conflict for the user), `implements` (decision → code area).

## Workflow (canonical sequence)

1. **Before creating**: `Grep -r "<3–5 keywords>" .manager_ai/memories/` — look for
   existing coverage. If a matching memory exists → `memory_update` it instead of
   creating a duplicate.
2. **Creating new**: decide parent. If none fits, create at root. Do not spawn a
   parent just to hold one child.
3. **Superseding**: do not delete the old memory silently. Either
   (a) update it in place with the new truth, or
   (b) create the new one and `memory_link(new, old, relation="supersedes")`, then
       edit the old memory's description to point at the new one.
4. **Contradiction**: if new info conflicts with an existing memory, surface it to
   the user before writing. Do not silently overwrite validated decisions.
5. **Verification**: a memory can be stale. If you are about to act on a memory that
   names a file/function/flag, verify it still exists (Grep / Read) before trusting it.

## Project scoping

Every MCP write call needs a `project_id` (or a `memory_id` which implies one). The
project id for the current workspace is in `manager.json` at the repo root. Never
cross project boundaries: `memory_link` rejects cross-project edges. Memories live
under the project's own `.manager_ai/memories/` folder — one project per folder.

## Anti-patterns

- Writing a memory mid-task "just in case" — wait until the fact is confirmed durable.
- Deep trees (> 3 levels). Prefer flat + links.
- Memories that paraphrase `CLAUDE.md`. Update `CLAUDE.md` instead.
- One memory per file. Memories are concepts, not a file index.
- Putting dates in titles ("2026-04-21 decision…"). Use `created_at` — it is already stored.
- Silent deletes. Prefer `supersedes` link so history is traceable.
- Hand-editing `memories.yaml` — it's derived. Edit the `.md` frontmatter instead.

## Quick reference

```
enumerate  → Read .manager_ai/memories.yaml
search     → Grep -ri "<keyword>" .manager_ai/memories/
read one   → Read .manager_ai/memories/<id>.md
write      → memory_create(project_id, title, description, parent_id?)     (MCP)
edit       → memory_update(memory_id, title?, description?, parent_id?)     (MCP)
graph      → memory_link(from_id, to_id, relation) / memory_unlink(...)     (MCP)
remove     → memory_delete(memory_id)                                       (MCP)
```
