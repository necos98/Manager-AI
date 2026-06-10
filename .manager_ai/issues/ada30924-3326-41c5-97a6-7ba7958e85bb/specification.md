## Micro-animazioni hover su cards, sidebar e bottoni

### Obiettivo
Aggiungere micro-animazioni di hover feedback visivo su tre categorie di elementi UI per rendere l'interfaccia più reattiva:
1. **Kanban cards** — leggero scale + shadow più pronunciata
2. **Sidebar items** — SidebarMenuButton con scale + shadow
3. **Bottoni** — tutti i bottoni con scale su hover

### Stato attuale
- **Kanban cards** (`kanban-card.tsx`): Hanno solo `transition-colors` + `hover:bg-accent/50`. Nessun effetto scale/shadow.
- **Sidebar items** (`sidebar.tsx` SidebarMenuButton): Hanno transizioni su `[width,height,padding]` e `hover:bg-sidebar-accent`. Nessun transform/shadow.
- **Bottoni** (`button.tsx`): Hanno `transition-all` già, ma nessun effetto scale su hover.

### Implementazione

#### 1. KanbanCard (kanban-card.tsx)
Sostituire la classe CSS del Card:
- `transition-colors` → `transition-all duration-200`
- Aggiungere `hover:scale-[1.01] hover:shadow-md`

#### 2. SidebarMenuButton (sidebar.tsx)
Modificare la stringa base di `sidebarMenuButtonVariants`:
- `transition-[width,height,padding]` → `transition-all duration-200`
- Aggiungere `hover:scale-[1.01] hover:shadow-sm`

#### 3. Button (button.tsx)
Modificare la stringa base di `buttonVariants`:
- Aggiungere `hover:scale-[1.02]`
- Aggiungere `hover:shadow-sm`

### Dettagli tecnici
- **Scala**: 1.01-1.02 per evitare overflow o artefatti visivi
- **Shadow**: `shadow-md` per cards (più pronunciato), `shadow-sm` per sidebar/buttons (sottile)
- **Durata**: 200ms (`duration-200`) per transizione fluida
- **Dark mode**: Le shadow Tailwind si adattano automaticamente al tema (usa OKLCH colors)
- **Nessun nuovo npm dep**: Solo classi Tailwind v4 esistenti

### Non incluso
- Le sidebar group action button (SidebarGroupAction) NON vengono modificate — hanno già `transition-transform` per altri scopi
- SidebarRail, SidebarTrigger, SidebarGroupLabel NON modificati — non sono elementi interattivi primari
