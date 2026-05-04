# Group Terminals by Project in Terminals Section

## Goal
On the `/terminals` page, group active terminal panels by project instead of showing a flat grid.

## Design

### Backend
No changes needed. `GET /api/terminals` already returns `project_id` and `project_name` per terminal.

### Frontend

**`terminal-grid.tsx`** — Group incoming terminals by `project_id` client-side. Render each group as:
- A project name header (small, muted)
- The group's terminals in a responsive grid below the header
- Per-group grid uses same `getGridClass` logic (1-2 terminals = fixed cols, 3+ = auto-fill)

**`terminals.tsx`** (route) — No data changes. Pass full terminal list to updated grid.

### Edge Cases
- **0 terminals**: Same empty state as today ("Nessun terminale attivo")
- **1 project, N terminals**: One header, N terminals in grid
- **N projects, 1 terminal each**: N headers, 1 terminal per group
- **Null project_name**: Fallback to "Unknown Project"
- **Ask & Brainstorm terminals** (issue_id=""): Included under their project normally

### Unchanged
- Individual terminal panel (xterm, toolbar, search, voice, files, copy)
- Kill button, Issue link
- Soft limit counter in page header
- WebSocket reconnection