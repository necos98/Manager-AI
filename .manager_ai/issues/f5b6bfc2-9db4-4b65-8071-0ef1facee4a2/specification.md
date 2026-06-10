# Issue: Modernizzare la sidebar — rimuovere gradienti e styling anni 90

## Riepilogo
La sidebar di Manager AI (sia AppSidebar che ProjectSidebar) ha uno styling che sembra "anni 90": gradienti lineari di sfondo, effetti hover con scale/shadow, e overall manca di quello stile pulito moderno che ci si aspetta da un'app 2026.

## Stato attuale

### CSS gradienti (index.css)
- `--sidebar-gradient: linear-gradient(180deg, oklch(...) 0%, transparent 100%)` — applicato su `[data-sidebar] { background-image: var(--sidebar-gradient); }`
- `--main-gradient: radial-gradient(ellipse at 50% 0%, ...)` — applicato su `.main-content-gradient`

### SidebarMenuButton (ui/sidebar.tsx)
- `transition-all duration-200 hover:scale-[1.01] hover:shadow-sm` — lo scale effetto hover è ciò che più grida "anni 2000"

## Cosa fare

### 1. Rimuovere gradienti dalle sidebar (index.css)
Rimuovere `--sidebar-gradient` e la regola `[data-sidebar] { background-image: ... }`. La sidebar deve avere sfondo piatto e pulito (usa già `bg-sidebar` via le classi shadcn).
Rimuovere `--main-gradient` e `.main-content-gradient`.

### 2. Modernizzare SidebarMenuButton (ui/sidebar.tsx)
Rimuovere `hover:scale-[1.01] hover:shadow-sm` dalla variante base di `sidebarMenuButtonVariants`. Tenere solo:
- `hover:bg-sidebar-accent hover:text-sidebar-accent-foreground` (già presente)
- `transition-colors duration-150` invece di `transition-all duration-200` — più snello
- Aggiungere `data-[active=true]:border-l-2 data-[active=true]:border-sidebar-primary` per un indicatore di attivo moderno (barra laterale sinistra)

### 3. Modernizzare SidebarGroupLabel (ui/sidebar.tsx)
- Aggiungere `uppercase tracking-wider` per un look più moderno
- Ridurre font-size a `text-[10px]`
- Aggiungere padding laterale per allineamento

### 4. Modernizzare Sidebar (la struttura)
- Tutte le sidebar hanno già `bg-sidebar` e border-right grazie a `group-data-[side=left]:border-r` — ok, va bene così
- Assicurarsi che la sidebar non abbia gradient residui

### 5. Sidebar content padding (app-sidebar.tsx / project-sidebar.tsx)
Aggiungere un leggero padding extra ai gruppi per migliorare la spaziatura. I `SidebarGroup` hanno già `p-2`, valutare se serve `gap-1` per i menu items.

### 6. SidebarHeader
- Migliorare lo header delle sidebar: già c'è un titolo, renderlo più pulito

## Cosa NON fare
- Non cambiare la logica di collapse/expand (funziona bene)
- Non cambiare la struttura dei SidebarProvider separati (serve per indipendenza)
- Non cambiare icone o layout dei link
- Non modificare la sidebar su mobile (Sheet)
- Non modificare SidebarGroupAction (ha già transition-transform)
- Non modificare SidebarRail (è già minimal)
