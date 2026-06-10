# Piano implementazione: Modernizzare sidebar

## Strategia
Modifiche mirate su 2 file: `frontend/src/index.css` e `frontend/src/shared/components/ui/sidebar.tsx`. Nessuna modifica ai componenti app-sidebar / project-sidebar (solo CSS e componenti base). Questo è sufficiente perché lo stile è centralizzato nel tema CSS e nel componente shadcn SidebarMenuButton.

## Task

### Task 1: Rimuovere gradienti da index.css
**File:** `frontend/src/index.css`
Rimuovere:
- `--sidebar-gradient` (entrambe light/dark)
- `--main-gradient` (entrambe light/dark)
- Regola CSS `[data-sidebar] { background-image: var(--sidebar-gradient); }`
- Regola CSS `.main-content-gradient { ... }`

### Task 2: Modernizzare SidebarMenuButton
**File:** `frontend/src/shared/components/ui/sidebar.tsx`
In `sidebarMenuButtonVariants`, sostituire:
- `transition-all duration-200 hover:scale-[1.01] hover:shadow-sm` → `transition-colors duration-150`
- Aggiungere indicatore active: `data-[active=true]:border-l-2 data-[active=true]:border-sidebar-primary pl-[calc(0.5rem-2px)]`

### Task 3: Modernizzare SidebarGroupLabel
**File:** `frontend/src/shared/components/ui/sidebar.tsx`
In `SidebarGroupLabel`, aggiungere classi:
- `uppercase tracking-widest text-[11px]` per label più moderne

### Task 4: Pulire classi gradient da __root.tsx
**File:** `frontend/src/routes/__root.tsx`
Rimuovere `main-content-gradient` dal div principale del contenuto.

### Task 5: Verifica
- `python -c "import ast; ast.parse(open('frontend/src/index.css').read())"` — non serve perché è CSS
- Verifica visiva: controllare che la build frontend passi
- Controllare che non rimangano riferimenti a gradient CSS
