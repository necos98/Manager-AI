## Recap: Sidebar collassabili icon-only

### Cosa è stato fatto

1. **`__root.tsx`** — Ogni sidebar ora ha il proprio `SidebarProvider` indipendente, con stato persistito in `localStorage` (chiavi `sidebar-project` e `sidebar-app`). Il mobile header ora usa un `Sheet` nativo per l'apertura della ProjectSidebar su mobile.

2. **`project-sidebar.tsx`** — Aggiunto `collapsible="icon"` al `<Sidebar>`, `SidebarRail` come handle di collapse sottile sul bordo, e `tooltip` su tutti i `SidebarMenuButton` (mostra il nome/navigazione al hover quando la sidebar è collassata).

3. **`app-sidebar.tsx`** — Stesse modifiche: `collapsible="icon"`, `SidebarRail`, `tooltip` su tutti i menu item.

### Come funziona

- **Indipendenza**: Ogni sidebar collassa/espande indipendentemente dall'altra
- **Persistenza**: Lo stato è salvato in `localStorage` e ripristinato al refresh
- **Tooltip**: In modalità icon-only, passando il mouse sulle icone appare il tooltip con il nome
- **Transizione**: Le sidebar hanno transizione fluida (`transition-[width] duration-200 ease-linear` fornita da shadcn)
- **Handle**: `SidebarRail` (strip verticale sottile sul bordo della sidebar) e scorciatoia `Ctrl/Cmd+B`

### Verifica
Build Vite completata con successo (2793 moduli, 0 errori).