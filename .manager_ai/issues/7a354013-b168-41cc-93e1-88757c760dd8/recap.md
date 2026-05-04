Modified `terminal-grid.tsx` to group terminals by project on the /terminals page.

Changes:
- Added `groupByProject()` — groups `TerminalListItem[]` by `project_id`, sorts groups alphabetically by project name
- Extracted `TerminalCard` component from inline JSX
- Groups render with a project name header (+ terminal count) and a per-group responsive grid
- Issue link hidden for Ask & Brainstorm terminals (no issue_id)
- Project name removed from card header (now redundant with group header)
- Outer container uses `space-y-6` + `overflow-auto` for scrollable grouped layout
- TypeScript compiles clean, zero lint errors

No backend changes needed. Single consumer (`/terminals` route), no API break.