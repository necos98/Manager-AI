# New Issue Dialog Polish — Design

**Date:** 2026-04-17
**Scope:** Visual polish of the "Create new issue" UI. Convert from full-page route to modal dialog with refined styling. No backend or schema changes.

## Goals

- Replace spartan `/projects/$projectId/issues/new` page with a modal dialog on the issues list page.
- Keep existing fields (`description`, `priority`) and their semantics unchanged.
- Align with shadcn/ui patterns already used elsewhere in the app.
- Reduce context switching: user stays on the kanban/issues list while creating.

## Non-Goals

- No new issue fields (name, tags, assignee, spec, plan).
- No wizard / multi-step flow.
- No AI-assisted prefill.
- No keyboard-shortcut global handlers outside the dialog.

## Architecture

### New file
- `frontend/src/features/issues/components/new-issue-dialog.tsx`
  - Props: `{ projectId: string; open: boolean; onOpenChange: (open: boolean) => void }`
  - Owns: local form state (`description`, `priority`), calls `useCreateIssue(projectId)`, closes on success.

### Changed file
- `frontend/src/routes/projects/$projectId/issues/index.tsx`
  - Owns `open` boolean state.
  - Replaces `<Button asChild><Link to=".../new">...</Link></Button>` with `<Button onClick={() => setOpen(true)}>`.
  - Renders `<NewIssueDialog projectId={projectId} open={open} onOpenChange={setOpen} />` at page root.

### Deleted file
- `frontend/src/routes/projects/$projectId/issues/new.tsx`
- TanStack Router's generated tree (`routeTree.gen.ts`) is regenerated automatically by the dev server / Vite plugin.

### Reused unchanged
- `useCreateIssue` hook (`features/issues/hooks.ts`).
- Backend schema `IssueCreate` (`description`, `priority`).
- `shared/components/ui/dialog.tsx`, `button.tsx`, `textarea.tsx`, `select.tsx`.

## Layout

`DialogContent` with `sm:max-w-lg`.

```
┌─────────────────────────────────┐
│ [FilePlus icon] New Issue       │  DialogHeader: icon + DialogTitle
│ Describe what needs to be done  │  DialogDescription (muted)
├─────────────────────────────────┤
│ Description *                   │  label
│ [Textarea, rows=5]              │
│                  {n} / 50000    │  live char count, right-aligned
│                                 │
│ Priority                        │  label
│ [ArrowUp] 1 (Highest)        ▼  │  Select trigger with leading icon
│                                 │
│ (error line if any, destructive)│
├─────────────────────────────────┤
│ ⌘↵ submit   [Cancel] [Create]   │  DialogFooter: hint left, buttons right
└─────────────────────────────────┘
```

### Priority icons (lucide-react)
| Priority | Label         | Icon          |
|----------|---------------|---------------|
| 1        | 1 (Highest)   | `ChevronsUp`  |
| 2        | 2             | `ChevronUp`   |
| 3        | 3             | `Equal`       |
| 4        | 4             | `ChevronDown` |
| 5        | 5 (Lowest)    | `ChevronsDown`|

Icon sizing: `size-4 text-muted-foreground`. Shown both in `SelectItem` rows and inside the `SelectTrigger` value rendering.

## Interactions

- **Open:** "New Issue" button sets `open=true`.
- **Submit:** form submit (button click) OR `Ctrl/Cmd+Enter` while focus is in the textarea. Shortcut handler attached on the textarea element only (not globally) to avoid interfering with Select dropdown keyboard nav.
- **Validation:** `description.trim().length > 0` required. "Create" button disabled when empty, when `description.length > 50000`, or when `createIssue.isPending`.
- **Char count:** `{description.length} / 50000`, `text-xs text-muted-foreground mt-1 text-right`. Turns `text-destructive` above 50000 (backend `_DESCRIPTION_MAX`).
- **Error:** `createIssue.error?.message` rendered above footer in `text-destructive`.
- **Success:** `onSuccess` closes the dialog, resets `description` and `priority` state, shows sonner toast `"Issue created"`. React Query invalidation already handled inside `useCreateIssue`; the kanban/list refreshes automatically. No navigation.
- **Cancel / Esc / outside click:** closes the dialog and resets form state.
- **Pending state:** dialog stays open, Create button shows `"Creating..."` and is disabled, Cancel stays enabled so user can dismiss if desired (mutation continues in background — already true today).

## Styling

- Header icon: `FilePlus` from lucide, `size-5 text-primary`, inline-flex with `DialogTitle`.
- Labels: `text-sm font-medium` with `mb-1.5`.
- Form spacing: `space-y-4` between field blocks.
- Footer: `flex justify-between items-center`; left side `<kbd>` hint with `text-xs text-muted-foreground`; right side button group.
- No `Card` wrapper — `DialogContent` already provides a surface.

## Data Flow

```
User clicks "New Issue"
  → setOpen(true)
  → NewIssueDialog renders controlled form
  → user types description / picks priority
  → submit (button or Cmd+Enter)
  → createIssue.mutate({ description, priority })
      → on success: reset form state, onOpenChange(false), toast
      → on error: render error message, stay open
```

## Error Handling

Errors surfaced via `createIssue.error` (already provided by `useCreateIssue`). No retries, no special-casing. Network error / validation error both render `error.message` inline.

## Testing

Manual verification only (no unit tests for this form today; matches current `new.tsx` coverage). Check:
- Opens on button click.
- Cmd/Ctrl+Enter submits from textarea.
- Esc / outside click closes and resets.
- Error message renders on forced failure.
- Kanban refreshes with new card after success.
- Priority value round-trips correctly (saved as integer, not string).
- Char counter correctly colors over 50000.

## Out of Scope / Future

- Keyboard shortcut (`n`) to open dialog from list — future.
- AI-drafted description prefill — future.
- Tag/label support — separate spec.
