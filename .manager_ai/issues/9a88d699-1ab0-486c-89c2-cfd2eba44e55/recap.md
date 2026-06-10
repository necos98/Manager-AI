## Richer Visual Theme — Completato

### Riepilogo
Tema visivo di Manager AI arricchito con:

1. **Brand accent color** — Sostituiti i colori accent/primary vanilla con un blu-viola brand (`oklch 265 hue`). Aggiornate le variabili `:root` e `.dark` per accent, primary, sidebar-accent, sidebar-primary sia in light che dark mode. Maggiore identità visiva.

2. **Gradienti sottili** — Aggiunto gradiente lineare verticale alle sidebar via CSS (`--sidebar-gradient`), e gradiente radiale sul main content area (`--main-gradient` + classe `main-content-gradient` in `__root.tsx`). Profondità visiva senza impattare contenuti.

3. **Micro-animazioni hover** — KanbanCard ora ha `hover:-translate-y-0.5 hover:shadow-md hover:border-accent/50` per effetto sollevamento con bordo brand. Transizioni `duration-200` fluide.

4. **Transizioni tema** — Body ha `transition: background-color 0.3s ease, color 0.3s ease` per cambio light/dark fluido. Classi `.card-hover-shadow` per ombre hover consistenti.

### File modificati
- `frontend/src/index.css` — variabili brand, gradienti, transizioni, hover shadows
- `frontend/src/routes/__root.tsx` — classe main-content-gradient
- `frontend/src/features/issues/components/kanban-card.tsx` — hover lift, shadow, border

### Build
Vite build completata con successo (2802 modules, 9.23s).
