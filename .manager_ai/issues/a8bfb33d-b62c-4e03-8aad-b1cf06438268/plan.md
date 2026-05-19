# Implementation Plan: Fix run-issue memory search

**Goal:** Sync `.claude/commands/run-issue.md` from `claude_resources/commands/run-issue.md` so steps 2 and 6 use filesystem `Grep` instead of non-existent `memory_search` MCP tool.

**Architecture:** Single file copy. `claude_resources/` is the source of truth; `.claude/` is the distribution copy. The source already has correct content — just needs to be propagated.

## Current state

`.claude/commands/run-issue.md` step 2:
```
Call `memory_search(project_id, query=...)`
```

`.claude/commands/run-issue.md` step 6:
```
call `memory_search` first to check for an existing memory
```

## Target state (from claude_resources/commands/run-issue.md)

Step 2:
```
Run `Grep -ri "<keywords>" .manager_ai/memories/` on the project root. 
If there are hits, `Read` the relevant `.manager_ai/memories/<id>.md` files
```

Step 6:
```
`Grep -ri "<keyword>" .manager_ai/memories/` first to check for an existing memory
```

## Verify

Confirm `.claude/commands/run-issue.md` no longer contains the string `memory_search`.