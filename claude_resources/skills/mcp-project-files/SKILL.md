---
name: mcp-project-files
description: Use when working on an issue or project that may have user-uploaded reference files (specs, PDFs, docs, spreadsheets, images). Teaches the correct discover → search → read workflow for the Manager AI MCP file tools (`list_project_files`, `search_project_files`, `read_project_file`) so uploaded materials actually get consulted instead of ignored.
---

# Manager AI — Project Files Workflow

Users attach reference files (requirements PDFs, design docs, CSVs, screenshots, legacy specs) to a project. These files are **not** part of the repo and **won't appear in `git ls-files` or codebase searches**. You must query them through MCP.

## When to invoke this skill

- Starting any issue (`get_next_issue` / `get_issue_details` returned something to work on).
- User mentions "the spec", "the document I uploaded", "the attached file", "the PDF", "the requirements", "the screenshot", etc.
- Writing a spec/plan (`create_issue_spec`, `create_issue_plan`) — uploaded files are primary source material.
- Answering a question where the answer could plausibly live in uploaded context rather than code.
- Before telling the user "I don't have that information" — check files first.

If unsure whether files exist: run `list_project_files`. Cheap call, eliminates guessing.

## The three tools

| Tool | Purpose | When |
|---|---|---|
| `list_project_files(project_id)` | Enumerate attached files + metadata | First. Always. Before assuming none exist. |
| `search_project_files(project_id, query, limit=20)` | FTS5 across filenames + extracted text | You have keywords but don't know which file |
| `read_project_file(project_id, file_id, offset=0, max_chars=50000)` | Fetch extracted text of one file | You know the target file (from list or search) |

## Mandatory workflow

```
list_project_files  →  (search_project_files)  →  read_project_file
```

Never call `read_project_file` with a guessed `file_id`. IDs come from `list_project_files` or `search_project_files` results only.

### Step 1 — Discover

Call `list_project_files(project_id)`. Inspect each record:

- `extraction_status`:
  - `ok` → text available, readable.
  - `pending` → extraction still running. Wait or skip; do not read yet.
  - `failed` → extraction broke. Surface `extraction_error` to user; cannot read.
  - `unsupported` → legacy `.doc`/`.xls` or unhandled type. Ask user to re-upload as `.docx`/`.xlsx`/PDF.
- `low_text: true` → file extracted but yielded minimal text (likely a scanned image / image-only PDF). Mention this to the user before drawing conclusions from it.
- `file_type` / `mime_type` / `original_name` → use to judge relevance without reading.

Do **not** dump the whole file list to the user unless asked. Use it internally to decide what to read.

### Step 2 — Target (pick one)

**Known filename or single obvious candidate** → skip search, go to Step 3 with that `id`.

**Many files / keyword hunt** → `search_project_files(project_id, query, limit=20)`. Craft the query like an FTS5 query: specific nouns/phrases from the issue, not full sentences. Inspect `snippet` + `rank` per hit to pick the real match. Re-query with different terms if top hits look irrelevant — do not force a wrong match.

### Step 3 — Read

`read_project_file(project_id, file_id)` returns at most `max_chars` (default 50000, cap 500000) starting at `offset`.

- `truncated: true` in response → more content remains. Paginate by calling again with `offset = previous_offset + len(content)` until `truncated: false` **only if** the tail is actually relevant to the task. Don't paginate blindly through a 400k-char file.
- `total_chars` tells you the full size up front — use it to decide whether to read all or grep via `search_project_files` instead.
- `status != "ok"` → handle as in Step 1.

## Integration with issue workflow

When about to call `create_issue_spec` or `create_issue_plan`:

1. `list_project_files` first.
2. Read/search anything whose name or content relates to the issue description.
3. Cite the source in the spec/plan body (e.g., "per `requirements_v3.pdf` §2.1, …") so the user can audit.
4. If an uploaded file contradicts the issue description, **ask the user** via `send_notification` before writing the spec — don't silently pick one.

## Anti-patterns

- ❌ Writing a spec/plan without calling `list_project_files` when the user has attached materials.
- ❌ Inventing a `file_id` or guessing filenames.
- ❌ Reading a 300k-char file in full when `search_project_files` would locate the relevant passage.
- ❌ Ignoring `extraction_status` and treating empty `content` as "file is empty".
- ❌ Treating `low_text: true` files as authoritative text — they're probably images/scans.
- ❌ Pasting raw file content back to the user unprompted. Summarize + cite; offer to quote on request.

## Error handling

- `{"error": "File not found"}` → the id is stale or wrong project. Re-list.
- Empty `content` with `status: "ok"` and `total_chars: 0` → extraction produced nothing (often scanned PDF). Tell the user and suggest re-upload or OCR.
- Every file-tool call must be tied to a real `project_id`. Get it from `get_project_context`, the current issue, or the conversation — never hardcode.

## Quick reference

```
# Always start here
files = list_project_files(project_id)

# Narrow by keyword when unsure
hits = search_project_files(project_id, "authentication flow OAuth")

# Pull text
doc = read_project_file(project_id, file_id, offset=0, max_chars=50000)
while doc["truncated"] and still_relevant:
    doc = read_project_file(project_id, file_id, offset=doc["offset"] + len(doc["content"]))
```
