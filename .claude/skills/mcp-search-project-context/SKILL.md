---
name: mcp-search-project-context
description: Use when you need to find relevant past issues, decisions, or knowledge stored in the Manager AI project context. Triggers on questions like "what did we do for X", "find related issues", "search project history", or when building on prior work.
---

# MCP Search Project Context

Reference skill for querying the Manager AI RAG (vector search) index via MCP tools.

## Prerequisites

Read `manager.json` in the project root for the `project_id` required by all MCP tools.

## Tools

### `mcp__ManagerAi__search_project_context`

Semantic (vector) search over embedded project knowledge (completed issues, specs, plans, recaps).

```
mcp__ManagerAi__search_project_context
  project_id:   <from manager.json>
  query:        <natural language query>
  source_type:  <optional: filter by type>
  limit:        <optional: number of results, default 5>
```

Returns a list of ranked chunks with IDs and snippets.

### `mcp__ManagerAi__get_context_chunk_details`

Retrieve full content of a specific chunk returned by a search.

```
mcp__ManagerAi__get_context_chunk_details
  project_id: <from manager.json>
  chunk_id:   <chunk ID from search results>
```

## Typical Flow

1. Read `project_id` from `manager.json`
2. Call `search_project_context` with a descriptive natural language query
3. Scan returned snippets — if a result looks relevant, call `get_context_chunk_details` for the full content
4. Use retrieved context to inform your answer or implementation

## Query Tips

- Be descriptive: `"authentication flow JWT token refresh"` beats `"auth"`
- Try multiple queries if first results are weak — rephrase or narrow the scope
- Use `source_type` to narrow results when you know the content type (e.g. `"issue"`)
- `limit` defaults to 5; increase it (up to ~20) when casting a wider net

## When Context is Not Indexed

Only **completed issues** are embedded (triggered by `complete_issue`). In-progress or new issues are not searchable via RAG — use `get_issue_details` instead.

## Common Mistakes

| Mistake | Fix |
|--------|-----|
| Skipping `get_context_chunk_details` for promising snippets | Always fetch full content before drawing conclusions |
| One vague query and giving up | Rephrase and retry with more specific terms |
| Assuming no results = no history | The issue may be open/in-progress; check via `get_issue_details` |
