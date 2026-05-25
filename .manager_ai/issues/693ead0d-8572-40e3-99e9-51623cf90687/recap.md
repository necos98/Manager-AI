## Changes

1. **`.gitignore`**: Added `.claude/worktrees/` entry — Claude Code creates worktrees under this directory. Without gitignore, worktree dirs show as untracked files in the main checkout.

2. **`.worktreeinclude`**: Created new file with `.env` pattern. Worktrees are fresh checkouts without gitignored files. `.worktreeinclude` tells Claude Code to copy matched gitignored files (like `.env`) into new worktrees, so they can connect to the database and run properly.

3. **`CLAUDE.md`**: Added worktree section documenting `--worktree` usage, `.worktreeinclude` purpose, cleanup behavior, and agent pipeline isolation approach.

## Key Decision

No `--worktree` flag in `ClaudeCodeExecutor`. The executor runs `claude -p` (non-interactive). Per Claude Code docs, `--worktree` + `-p` worktrees are never auto-cleaned — they would leak on every agent step. Instead, agent pipeline isolation works at the session level: run `claude --worktree` and all agent `claude -p` subprocesses naturally run inside the isolated worktree.

## Non-changes

- No `worktree.baseRef` config — default `"fresh"` (branch from origin/HEAD) is correct
- No `cleanupPeriodDays` — only affects orphaned subagent worktrees, not `--worktree` sessions
- No agent model `isolation` field — Manager AI agents are DB records, not Claude Code subagent frontmatter