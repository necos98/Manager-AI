# Specification: Fix "Memory tools limited — skipping search" in run-issue

## Problem

When the LLM runs `/run-issue`, step 2 says to call `memory_search(project_id, query=...)` — an MCP tool that **does not exist** in the Manager AI MCP server. The LLM looks for this tool, can't find it, and says "Memory tools limited — skipping search." Same issue in step 6 for memory write verification.

## Root Cause

`.claude/commands/run-issue.md` references MCP tools `memory_search` and `memory_get` that are not exposed. The source-of-truth file `claude_resources/commands/run-issue.md` already has the correct approach: filesystem-based search via `Grep -ri`.

The `.claude/` copy is stale — it was not updated when `claude_resources/` was changed.

## Fix

Sync `.claude/commands/run-issue.md` from `claude_resources/commands/run-issue.md`:

1. **Step 2**: Change `memory_search(project_id, query=...)` → `Grep -ri "<keywords>" .manager_ai/memories/` followed by `Read` of matching `.md` files
2. **Step 6**: Change `memory_search` for write verification → `Grep -ri "<keyword>" .manager_ai/memories/`

The `Grep` tool is always available to Claude Code (it's a native tool). The `.manager_ai/memories/` directory contains plain markdown files readable via `Read` — no MCP needed.

## Verify

After sync, run `/run-issue` on any issue and confirm step 2 executes without the "Memory tools limited" message.