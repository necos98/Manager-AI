## Recap: Micro-animazioni hover su cards, sidebar e bottoni

### Cosa è stato fatto
Aggiunte micro-animazioni hover su 3 categorie di elementi UI:

1. **Button** (`button.tsx`): Aggiunto `hover:scale-[1.02]` e `hover:shadow-sm` alla stringa base `buttonVariants`. Tutti i bottoni ora hanno un leggero scale e ombra al passaggio del mouse.

2. **SidebarMenuButton** (`sidebar.tsx`): Cambiato `transition-[width,height,padding]` → `transition-all duration-200` e aggiunto `hover:scale-[1.01] hover:shadow-sm`. Sidebar items hanno ora transizione fluida su tutte le proprietà.

3. **KanbanCard** (`kanban-card.tsx`): Cambiato `transition-colors` → `transition-all duration-200` e aggiunto `hover:scale-[1.01] hover:shadow-md`. Cards kanban ora scalano leggermente e mostrano ombra più pronunciata all'hover.

### Verifica
- `npx tsc --noEmit`: 0 errori — TypeScript check passato
- Tutte le modifiche sono classi Tailwind v4 standard, nessun nuovo npm dependency

### Dettagli tecnici
- **Scala**: 1.01 per cards/sidebar (minimo, senza overflow), 1.02 per bottoni (più reattivo al click)
- **Shadow**: `shadow-md` per cards (più pronunciato), `shadow-sm` per sidebar/buttons
- **Durata**: 200ms per tutte le transizioni
- **Dark mode**: Le shadow Tailwind si adattano automaticamente al tema via variabili CSS OKLCH