## Piano di implementazione: Sidebar collassabili icon-only

### Approccio tecnico

Usiamo le funzionalità built-in di shadcn/ui sidebar:
- `collapsible="icon"` già supportato dal componente `Sidebar`
- `SidebarRail` per il toggle collapse (strip sottile sul bordo)
- `SidebarMenuButton` supporta già `tooltip` prop per mostrare label al hover quando collapsed
- Transizioni CSS già presenti (classe `transition-[width] duration-200 ease-linear`)

Per l'indipendenza dei due collapse: ogni sidebar ottiene il proprio `SidebarProvider` con stato controllato (`open`/`onOpenChange`) persistito in localStorage con chiave separata.

### Task

1. **Split SidebarProvider in `__root.tsx`** — Separare il singolo SidebarProvider in due provider indipendenti (uno per ProjectSidebar, uno per AppSidebar). Aggiungere hook di stato localStorage per-sidebar.

2. **Modificare `project-sidebar.tsx`** — Aggiungere `collapsible="icon"` al `<Sidebar>`, inserire `<SidebarRail />` come handle collapse, aggiungere prop `tooltip` ai `SidebarMenuButton`.

3. **Modificare `app-sidebar.tsx`** — Stesse modifiche: `collapsible="icon"`, `<SidebarRail />`, tooltip sui menu button.

4. **Verifica** — Controllare che il frontend compili e che le sidebar collassino indipendentemente.