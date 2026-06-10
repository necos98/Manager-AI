## Implementation Plan

### Task 1: Creare QuickCreateIssueDialog
- File: `frontend/src/features/issues/components/quick-create-issue-dialog.tsx`
- Dialog minimal con:
  - Textarea per descrizione (autoFocus, 3 righe)
  - Priority Select (default 3)
  - Pulsante Cancel + Create (con loading state)
  - Submit via click Create o Ctrl+Enter
  - Reset on close (nessun abandon-confirmation — quick create non richiede conferma)
  - Su successo: toast "Issue created", chiude dialog
- Riutilizza `useCreateIssue` hook

### Task 2: Aggiungere pulsante "+" nella ProjectSidebar
- File: `frontend/src/shared/components/project-sidebar.tsx`
- In `ProjectSidebarItem`, aggiungere SidebarMenuAction con icona Plus
- SidebarMenuAction apre lo stato quickCreateOpen per quel progetto
- QuickCreateDialog renderizzato inline nel sidebar item o sollevato a ProjectSidebar
- Tooltip "Quick create issue"

### Task 3: Verifica build
- `cd frontend && npm run lint` per verificare che non ci siano errori
