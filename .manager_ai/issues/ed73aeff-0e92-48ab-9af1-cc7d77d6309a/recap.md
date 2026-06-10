## Recap: Quick Create Issue dalla Sidebar

### Cosa è stato fatto

**Task 1: QuickCreateIssueDialog** (nuovo componente)
- Creato `frontend/src/features/issues/components/quick-create-issue-dialog.tsx`
- Dialog minimal con solo: textarea descrizione (3 righe), priority select (default 3), pulsanti Cancel/Create
- Submit via click Create o Ctrl+Enter
- Reset del form alla chiusura
- Nessun campo Tags, Category, Browse Files, Voice
- Nessun abandon-confirmation (quick create non richiede conferma)
- Riutilizza `useCreateIssue` hook esistente
- Toast "Issue created" su successo

**Task 2: Pulsante "+" nella ProjectSidebar**
- Modificato `frontend/src/shared/components/project-sidebar.tsx`
- Aggiunto SidebarMenuAction con icona Plus accanto allo star/favorite in ogni ProjectSidebarItem
- Tooltip "Quick create issue"
- Stato `quickCreateProjectId` gestito a livello di ProjectSidebar
- QuickCreateIssueDialog renderizzato alla fine del componente, aperto quando quickCreateProjectId non è null

**Task 3: Verifica**
- TypeScript type check senza errori nei file modificati

### Design decisions
- Componente separato (QuickCreateIssueDialog) invece di parametrizzare NewIssueDialog — evita di complicare il dialog full-featured
- Dialog aperto a livello di ProjectSidebar (non inline nel sidebar item) — un solo dialog, stato centralizzato
- Nessun abandon-confirmation — il quick create è talmente veloce che la conferma sarebbe un attrito inutile
- Keyboard shortcut `n` non implementata — valutare come miglioramento futuro
