# Optimize Claude Code Worktree Usage

## Goal

Configure Manager AI project for proper Claude Code worktree support and enable subagent worktree isolation for the agent pipeline.

## Section 1: Project Configuration

### 1.1 `.gitignore` — Add `.claude/worktrees/`

**Current state:** `.gitignore` ignores `.worktrees/` but not `.claude/worktrees/`.

**Change:** Add `.claude/worktrees/` to `.gitignore`.

**Why:** Claude Code creates worktrees under `.claude/worktrees/` by default. Without the gitignore entry, worktree directories appear as untracked files in the main checkout. The Claude Code documentation explicitly states: "Add `.claude/worktrees/` to your `.gitignore` so worktree contents don't appear as untracked files in your main checkout."

### 1.2 `.worktreeinclude` — Create new file

**Current state:** File does not exist. Worktrees are missing `.env` and potentially other gitignored config files.

**Change:** Create `.worktreeinclude` at project root with gitignore-style patterns for files that worktrees need:
```
.env
```

**Why:** A worktree is a fresh checkout from the branch. Gitignored files (like `.env`) are not present. `.worktreeinclude` tells Claude Code to copy matched gitignored files from the main checkout into new worktrees. Without `.env`, the worktree session can't connect to the database or run properly.

**Scope:** Applies to `--worktree` sessions, subagent worktrees, and parallel desktop app sessions. Only files that match a pattern AND are gitignored are copied — tracked files are never duplicated.

### 1.3 `worktree.baseRef` — Keep default `"fresh"`

**Current state:** No `worktree.baseRef` set — defaults to `"fresh"`.

**Decision:** Keep default. Do NOT set `"head"`.

**Why:** Default `"fresh"` branches from `origin/HEAD` (the repo's default branch), giving each worktree a clean starting tree. `"head"` would carry unpushed commits and feature-branch state, which is undesirable for agent worktrees that should start from a known clean state.

## Section 2: Agent Worktree Isolation

### 2.1 Enable `isolation: worktree` on custom subagents

**Current state:** Manager AI has agent roles (SpecWriter, Architect, Developer, Reviewer, QA) in the pipeline. No worktree isolation is configured.

**Change:** Add `isolation: worktree` to the frontmatter of relevant custom subagents.

**Why:** Without isolation, parallel subagent runs in the same session share a working directory — file edits from one agent can conflict with another. Worktree isolation gives each subagent its own working directory with independent file state. Clean worktrees are auto-removed; worktrees with changes prompt for keep/remove.

**Lifecycle behavior:**
- Subagent gets a temporary worktree, auto-removed when finished without changes
- Orphaned worktrees (from crashes) cleaned up at startup after `cleanupPeriodDays`
- Worktrees created with `--worktree` are never removed by the sweep

### 2.2 Set `cleanupPeriodDays`

Add `cleanupPeriodDays: 3` to project settings. Orphaned subagent worktrees older than 3 days with no uncommitted changes, untracked files, or unpushed commits are removed at startup.

### 2.3 Terminal service compatibility

**Risk:** Current agent execution uses terminal service (PTY via pywinpty). Worktree isolation changes working directory — terminal service must resolve paths correctly in worktree context.

**Mitigation:** No changes needed if `project.path` is resolved at runtime and the terminal service doesn't hardcode the main checkout path. Verify during implementation.

## Section 3: Documentation

### 3.1 CLAUDE.md — Add worktree section

Add a concise worktree section documenting:
- How to use `--worktree` flag for parallel sessions
- What `.worktreeinclude` does
- Cleanup behavior (auto-remove when clean, prompt when dirty)
- Agent worktree isolation in the pipeline

## Non-Goals

- No MCP tools for worktree management (git CLI already handles this)
- No worktree status dashboard in frontend
- No `worktree.baseRef: "head"` (clean default is better for this project)
