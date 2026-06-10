## Specifica tecnica: Tema visivo più ricco per Manager AI

### Contesto
Il frontend di Manager AI usa Tailwind v4 + shadcn/ui con CSS custom properties (oklch). Attualmente il tema è vanilla shadcn: sfondo bianco puro (`--background: oklch(1 0 0)`), nessun gradiente, ombre minime. L'architettura CSS è basata su variabili `:root` (light) e `.dark` (dark) in `frontend/src/index.css`. Il layout usa doppia sidebar indipendente (ProjectSidebar + AppSidebar) con SidebarProvider separati in `__root.tsx`.

### Obiettivi

#### 1. Subtle gradient su sidebar e sfondo principale
- **Sidebar sinistra (ProjectSidebar + AppSidebar):** Aggiungere un gradiente lineare verticale molto tenue (`--sidebar-background` modificato con gradiente sovrapposto). Il gradiente va da un colore leggermente accentato in alto a trasparente in basso.
- **Main content area:** Aggiungere un gradiente radiale molto tenue centrato (`background-image: radial-gradient(...)`) sul main content, visibile solo quando lo sfondo è liscio.
- I gradienti devono rispettare light/dark: nella modalità dark usare tonalità più scure del colore brand.

#### 2. Ombre più pronunciate su hover cards
- **KanbanCard** (`kanban-card.tsx`): Aggiungere classi `hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200` per effetto sollevamento.
- **Card generiche** (shadcn `Card`): Il componente Card shadcn usa variabili CSS per ombre. Arricchire le ombre hover via CSS custom properties.
- **Issue detail, dialog cards:** Stessa logica — hover shadow più marcata.

#### 3. Accent color brand-specific per Manager AI
- Sostituire il colore accent vanilla (grigio neutro) con un blu-viola brand.
- **Light mode (`:root`):**
  - `--accent`: da `oklch(0.967 0.001 286.375)` a `oklch(0.9 0.05 265)` (blu lavanda chiaro)
  - `--accent-foreground`: da `oklch(0.141 0.005 285.823)` a `oklch(0.15 0.02 265)`
  - `--primary`: da `oklch(0.141 0.005 285.823)` a `oklch(0.35 0.12 265)` (blu brand per bottoni primari)
- **Dark mode (`.dark`):**
  - `--accent`: da `oklch(0.274 0.006 286.033)` a `oklch(0.25 0.08 265)`
  - `--primary`: da `oklch(0.985 0 0)` a `oklch(0.65 0.15 265)`
- **Sidebar variables:** Aggiornare `--sidebar-accent` e `--sidebar-primary` per coerenza.

#### 4. Micro-animazioni su hover cards
- Aggiungere `hover:border-accent` sulle card Kanban e dialog (bordo brand al posto del bordo grigio).
- Aggiungere `transition-all duration-200` sulle card per animazioni fluide.
- Aggiungere `hover:shadow-md` su sidebar items interattivi.

#### 5. Transizioni di stato più fluide
- Aggiungere `transition-colors duration-200` su badge e indicatori di stato.
- Aggiungere `transition-shadow duration-200` su card e contenitori interattivi.
- Aggiungere `transition-colors duration-300` sul body per transizioni light→dark fluide.

### File da modificare
1. `frontend/src/index.css` — variabili CSS (:root e .dark), gradienti, transizioni base
2. `frontend/src/features/issues/components/kanban-card.tsx` — hover shadow, bordo, transizioni
3. `frontend/src/routes/__root.tsx` — aggiungere classe/gradiente sul main content area

### Non modificare
- Non alterare la struttura HTML/JSX (solo classi CSS e variabili)
- Non modificare il sistema di routing o layout generale
- Non toccare la sidebar component logic o SidebarProvider
- Non introdurre nuove dipendenze
- Non fare modifiche backend
