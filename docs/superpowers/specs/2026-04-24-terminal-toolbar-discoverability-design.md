# Terminal Toolbar Discoverability — Design

## Problem

Toolbar buttons in `TerminalPanel` are too subtle:
- Height: `h-6` (24px) — too small
- Text color: `text-zinc-400` — low contrast against dark background
- Buttons blend into the terminal header, hard to notice at a glance

## Solution (Option A — Moderate Lift)

Make toolbar buttons easier to spot without redesigning the layout.

### Changes

**Toolbar container (line ~277):**
- Background: `bg-zinc-900` → `bg-zinc-800/40` (subtle tint, not full bg change)

**Button props (lines ~278-333):**
- Height: `h-6` → `h-8`
- Text color: `text-zinc-400` → `text-zinc-200`
- Keep ghost variant (no bg by default)
- Hover stays, but transition made snappier: 150ms

### Files

- `frontend/src/features/terminals/components/terminal-panel.tsx`

### Scope

Visual refinement only — no behavior change, no new functionality.
