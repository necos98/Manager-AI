# Component Inventory — Frontend

**Part:** frontend
**Project Type:** React/TypeScript (Web)
**Generated:** 2026-06-07

## UI Primitives (src/shared/components/ui/)

| Component | File | Description |
|-----------|------|-------------|
| Badge | badge.tsx | Status/category badges |
| Button | button.tsx | Primary action button |
| Card | card.tsx | Content container card |
| Collapsible | collapsible.tsx | Expandable sections |
| Dialog | dialog.tsx | Modal dialogs (Radix) |
| DropdownMenu | dropdown-menu.tsx | Context menus (Radix) |
| Input | input.tsx | Text input |
| Resizable | resizable.tsx | Split panels |
| ScrollArea | scroll-area.tsx | Custom scroll area |
| Select | select.tsx | Dropdown select (Radix) |
| Separator | separator.tsx | Visual divider |
| Sheet | sheet.tsx | Side panel (Radix) |
| Sidebar | sidebar.tsx | Navigation sidebar |
| Skeleton | skeleton.tsx | Loading placeholder |
| Sonner | sonner.tsx | Toast notifications |
| Tabs | tabs.tsx | Tab navigation (Radix) |
| Textarea | textarea.tsx | Multi-line input |
| Tooltip | tooltip.tsx | Hover tooltip (Radix) |

**Design System:** Radix UI primitives wrapped with Tailwind CSS 4 + `cn()` utility (clsx + tailwind-merge) for className merging.

## Layout Components (src/shared/components/)

| Component | Description |
|-----------|-------------|
| app-sidebar.tsx | Main app navigation sidebar |
| project-sidebar.tsx | Project-scoped navigation |
| error-boundary.tsx | React error boundary |
| markdown-viewer.tsx | Markdown rendering via react-markdown |
| smartphone-qr-dialog.tsx | QR code for mobile access |
| speech-modal.tsx | Voice input modal (Whisper) |
| theme-toggle.tsx | Dark/light mode toggle |
| ImportPreviewModal.tsx | Data import preview |

## Feature Components

### Issues
Issue CRUD, status transitions, feedback forms, priority/category display
### Projects
Project dashboard, settings, archive/unarchive, health checks
### Terminals
Xterm.js terminal emulator with toolbar, WebSocket I/O streaming
### Agents
Agent configuration, import/export, seeding defaults
### Pipelines
Pipeline builder with drag-and-drop steps (via @dnd-kit)
### Pipeline Runs
Run monitoring, message threads, status tracking
### Files
File upload, gallery, preview (PDF/DOCX/XLSX), search with extracted text
### Settings
Global and project-scoped settings editor
### Credentials
Encrypted credential management with presets
### Memories
Memory CRUD with link graph (via reactflow/dagre)
### Library
Skill library browser
### Questions
Agent→human question/answer workflow

## Shared Components

- **src/shared/components/ui/** — 18 Radix-based primitives
- **src/shared/components/** — 8 app-level components
- **Feature components** — Colocated in `src/features/{name}/components/`

## Routing (src/routes/)

File-based routing via TanStack Router:
- `__root.tsx` — Root layout
- Dynamic segments with `$` prefix
- Router devtools in development
