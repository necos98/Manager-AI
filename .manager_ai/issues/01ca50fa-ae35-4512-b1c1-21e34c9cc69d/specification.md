## Specifica: Sidebar collassabili icon-only

### Problema
Attualmente entrambe le sidebar (ProjectSidebar + AppSidebar) occupano 220px + 260px = 480px fissi di navigazione. Su schermi 1366px è circa il 32% dello spazio sprecato per la navigazione, riducendo l'area utile per il contenuto principale.

### Obiettivo
Rendere entrambe le sidebar collassabili a icon-only (pattern VSCode/Linear), con:
1. Pulsante collapse indipendente per ogni sidebar
2. Stato persistito in localStorage (per-sidebar)
3. Tooltip al hover quando in modalità icon-only
4. Transizione fluida (shadcn già la fornisce)

### Architettura

**Stato attuale (da memoria bd2aff40):**
- Doppia sidebar con SidebarProvider annidati (o singolo provider condiviso)
- ProjectSidebar: 220px, elenco progetti + nav globale
- AppSidebar: 260px, nav specifica del progetto
- Entrambe condividono lo stesso stato expanded/collapsed

**Cosa cambia:**
- Ogni sidebar ottiene il proprio SidebarProvider per stato di collapse indipendente
- Usiamo `collapsible="icon"` di shadcn/ui (già built-in nel componente Sidebar)
- SidebarRail come handle di collapse (strip verticale sottile sul bordo)
- SidebarMenuButton tooltip prop per mostrare label al hover in modalità icon-only
- Stato salvato in localStorage con chiave per-sidebar (es. `sidebar-project`, `sidebar-app`)
- SidebarTrigger mobile (esistente) agganciato alla sidebar più esterna

### File coinvolti

1. **`frontend/src/routes/__root.tsx`** — Layout: split SidebarProvider in provider separati per sidebar
2. **`frontend/src/shared/components/project-sidebar.tsx`** — Add `collapsible="icon"`, SidebarRail, tooltip
3. **`frontend/src/shared/components/app-sidebar.tsx`** — Add `collapsible="icon"`, SidebarRail, tooltip

### Non incluso (fuori scope)
- Sidebar per mobile (già gestita da shadcn con Sheet) — rimane invariata
- Temi/colori — nessuna modifica stilistica
- Riordino voci nav