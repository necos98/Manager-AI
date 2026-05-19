## Fix

Synced `.claude/commands/run-issue.md` from `claude_resources/commands/run-issue.md`. 

### What changed

Steps 2 and 6 now use filesystem-based `Grep -ri` to search `.manager_ai/memories/` instead of non-existent MCP tools `memory_search`/`memory_get`.

### Root cause

`.claude/commands/run-issue.md` was stale — still referenced `memory_search` MCP tool that doesn't exist in Manager AI's MCP server. The source-of-truth in `claude_resources/commands/run-issue.md` was already correct.

### Verification

Zero matches for `memory_search` or `memory_get` in the fixed file. Both steps now use native Claude Code `Grep` tool which is always available.