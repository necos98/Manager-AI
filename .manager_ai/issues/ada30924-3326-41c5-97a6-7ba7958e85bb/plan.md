## Piano implementazione: Micro-animazioni hover

### Modifiche da apportare (3 file)

#### Task 1: Button — hover scale + shadow
**File:** `frontend/src/shared/components/ui/button.tsx`
- Aggiungere `hover:scale-[1.02]` e `hover:shadow-sm` alla stringa base di `buttonVariants` (line 8)

#### Task 2: SidebarMenuButton — hover scale + shadow
**File:** `frontend/src/shared/components/ui/sidebar.tsx`
- Modificare `transition-[width,height,padding]` → `transition-all duration-200` nella stringa base di `sidebarMenuButtonVariants` (line 475)
- Aggiungere `hover:scale-[1.01] hover:shadow-sm`

#### Task 3: KanbanCard — hover scale + shadow
**File:** `frontend/src/features/issues/components/kanban-card.tsx`
- Sostituire `transition-colors` con `transition-all duration-200` (line 81)
- Aggiungere `hover:scale-[1.01] hover:shadow-md`

### Ordine esecuzione
1. button.tsx (Task 1) — più semplice, tocca solo la stringa base
2. sidebar.tsx (Task 2) — richiede attenzione alla transizione lista
3. kanban-card.tsx (Task 3) — modifica più visibile

### Verifica
Dopo l'implementazione, verificare che il frontend compili senza errori:
```bash
cd frontend && npm run lint
```
