# Implementation Plan: Optimize Claude Code Worktree Usage

## Overview

Three config changes + CLAUDE.md docs. No executor code changes — `--worktree` flag in executor leaks orphaned worktrees (`-p` mode never cleans up). Agent worktree isolation works at session level: run `claude --worktree` and all agent steps run isolated.

## Task 1: Update .gitignore

**File:** Modify `.gitignore`

Add `.claude/worktrees/` entry. Claude Code creates worktrees under this directory by default. Without gitignore, they show as untracked files.

Change: Add `.claude/worktrees/` line next to existing `.worktrees/` line (line 29).

## Task 2: Create .worktreeinclude

**File:** Create `.worktreeinclude` at project root

Worktrees are fresh checkouts — gitignored files like `.env` are missing. `.worktreeinclude` tells Claude Code to copy matched gitignored files into new worktrees.

Content:
```
.env
```

Only `.env` needed. Other gitignored dirs (`node_modules/`, `.venv/`, `data/`) should NOT be copied — they're build artifacts, not config.

## Task 3: Update CLAUDE.md

**File:** Modify `CLAUDE.md`

Add worktree section covering:
- `--worktree` flag for parallel sessions
- `.worktreeinclude` purpose
- Worktree cleanup behavior
- Agent pipeline worktree isolation (session-level: run `claude --worktree` and agents inherit isolation)

## Non-changes (with rationale)

- **No `worktree.baseRef` change**: default `"fresh"` is correct — clean branch from `origin/HEAD`
- **No `cleanupPeriodDays` in settings**: only affects orphaned subagent worktrees, not `--worktree` sessions
- **No executor `--worktree` flag**: `-p` mode never cleans up worktrees, would leak on every agent step
- **No agent `isolation` field**: Manager AI agents are DB records, not Claude Code subagent frontmatter