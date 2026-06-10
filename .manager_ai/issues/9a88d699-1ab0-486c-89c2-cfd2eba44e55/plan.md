## Piano di implementazione: Tema visivo più ricco

### Task 1: Brand accent color — aggiornare variabili CSS in `index.css`
- Modificare `--accent`, `--accent-foreground`, `--primary`, `--primary-foreground` in `:root` e `.dark`
- Stessa modifica per `--sidebar-accent`, `--sidebar-accent-foreground`
- **File:** `frontend/src/index.css`

### Task 2: Gradienti su sidebar e sfondo principale
- Aggiungere gradiente lineare verticale alle sidebar via CSS background-image su `.sidebar` (classe shadcn)
- Aggiungere gradiente radiale tenue sul main content area in `__root.tsx`
- **File:** `frontend/src/index.css`, `frontend/src/routes/__root.tsx`

### Task 3: Ombre e micro-animazioni sulle card Kanban
- Aggiungere `hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200` alla KanbanCard
- Aggiungere `hover:border-accent/50` per bordo brand su hover
- **File:** `frontend/src/features/issues/components/kanban-card.tsx`

### Task 4: Transizioni fluide globali
- Aggiungere `transition-colors duration-300` sul body per cambio tema fluido
- Aggiungere variabili `--transition-colors` e `--transition-shadow` per consistenza
- Aggiungere ombra hover via CSS personalizzato per componenti shadcn Card
- **File:** `frontend/src/index.css`

### Task 5: Verifica build frontend
- Eseguire `npm run lint` per verificare che non ci siano errori
- Verificare sintassi Tailwind v4
