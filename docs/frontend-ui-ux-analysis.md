# Frontend UI/UX Analysis — Manager AI

**Data:** 10 Giugno 2026
**Stack:** React 19 + Vite 5 + Tailwind CSS 4 + TanStack Router + TypeScript 6 + Radix UI/shadcn

---

## Stack & Architettura

| Layer | Tecnologia |
|-------|-----------|
| Framework | React 19 |
| Bundler | Vite 5 |
| Styling | Tailwind CSS 4 + `class-variance-authority` |
| Routing | TanStack Router (file-based, typesafe) |
| Server State | TanStack React Query |
| UI Library | Radix UI / shadcn components |
| Icone | lucide-react |
| Drag & Drop | @dnd-kit |
| Terminale | xterm.js + @xterm/addon-fit/search/web-links |
| Tema | next-themes (dark/light/system) |
| Layout | react-resizable-panels |
| Notifiche | sonner (toast) |
| Markdown | react-markdown |

---

## ✅ Punti di Forza

### Architettura
- Feature-based folder structure (`features/`, `shared/`, `routes/`) — scalabile e ben organizzata
- TanStack Router con route tree generato automaticamente e typing
- React Query per caching e sincronizzazione server
- Invalidazioni real-time via WebSocket EventProvider
- Resizable panels per layout split issue+terminale
- Dark/light theme completo
- Codice TypeScript strict con tipi condivisi

### Feature UI
- Kanban board con drag & drop e validazione transizioni
- Terminale interattivo via WebSocket (search, fit, web-links, speech input)
- Inline editing (nome, priorità, descrizione, tags)
- Speech-to-text in creazione issue e terminale
- Pipeline progress con step runner live e terminal output
- Coda issue globale con pulsazione live
- Activity timeline, memory tree, file gallery
- Provider configuration, MCP setup, Telegram integration
- Issue relations graph (dagre)
- Drag overlay feedback visivo

---

## 🔴 Criticità UI

### 1. Tema visivo piatto
Il tema shadcn è vanilla: sfondo bianco, nessun gradiente, nessuna texture. Cards e componenti mancano di profondità.

**Suggerimenti:**
- Subtle gradient su sidebar o sfondo principale
- `shadow-md` su hover delle cards invece di `shadow-sm` fisso
- Accent color brand-specific invece del nero/grigio
- Micro-animazioni su hover (scale, border glow)

### 2. Nessun layout mobile
Sidebar non collassabile su mobile (il `SidebarTrigger` è nascosto su `md:`). Kanban board non fruibile sotto i 1024px.

**Suggerimenti:**
- Sidebar collassabile icon-only (pattern VSCode/Linear)
- Su mobile: Kanban → lista verticale con filtri ad accordion
- Bottom navigation su mobile invece di doppia sidebar
- Issue detail con tab verticali invece di resizable panels

### 3. Doppia sidebar troppo ingombrante
ProjectSidebar (~220px) + AppSidebar (~220px) = **440px fissi**. Su 1366px è il 32% dello schermo per navigazione.

**Suggerimenti:**
- Sidebar collassabile a icon-only (stato salvato in localStorage)
- Sidebar unificata: icone globali + progetti + pagine progetto in un solo pannello
- Ridurre larghezza default a 180px

### 4. Dashboard povero
Mostra solo una griglia con project name e issue attive. Nessuna metrica.

**Suggerimenti:**
- Metriche: issue completate/7gg, tempo medio completamento, pipeline fail rate
- Grafico a barre dello stato issue per progetto
- Activity feed globale (ultime 24h)
- Widget "In esecuzione ora" con pulse green dot

### 5. Stati loading/empty generici
Loading: solo `<Skeleton>` senza shimmer. Empty: solo testo ("No issues yet").

**Suggerimenti:**
- Skeleton con forme che rispecchiano il contenuto finale
- Empty state con illustrazione + CTA guida ("Crea la tua prima issue")
- Error state con pulsante Retry e messaggio user-friendly

### 6. Filtri Kanban poco visibili
Search, priority, tag, sort sono in una riga di select sopra la board. Su schermi stretti si rompono.

**Suggerimenti:**
- Pannello filtri collassabile
- Filtro full-text rapido nell'header (Cmd+K)
- Filtro per agente/assegnatario
- Salvataggio preferiti di filtro per progetto

---

## 🧠 Criticità UX

### 7. Nessuna scorciatoia da tastiera
Solo `⌘↵` per submit. Nessuna navigazione rapida.

**Priorità ALTA:**
- `n` → New issue
- `/` o `Cmd+K` → Command palette / ricerca globale
- `g` `i` → Go to Issues, `g` `d` → Dashboard
- `Esc` → Chiudi modale / deseleziona
- `?` → Mostra shortcut
- `1-5` → Set priority veloce

### 8. Nessuna ricerca globale
Search esiste solo dentro la Kanban board per-progetto.

**Suggerimenti:**
- Command palette (Cmd+K) stile Linear/VSCode
- Global search su progetti, issue, pagine
- Risultati raggruppati per progetto

### 9. Nessuna azione bulk
Non puoi selezionare più issue per cambiarle status, tag, o eliminarle in blocco.

**Suggerimenti:**
- Checkbox sulle kanban cards (toggle mode)
- Action bar che compare con selezione attiva
- "Select all in column"

### 10. Breadcrumb assenti
Nessuna indicazione di posizione nella gerarchia di navigazione.

**Suggerimenti:**
- Breadcrumb: `Projects > NomeProgetto > Issues > TitoloIssue`
- Breadcrumb cliccabile per risalire

### 11. Agent Chat sepolto
6° tab nell'issue detail, visibile solo se ci sono pipeline runs. Poco scopribile.

**Suggerimenti:**
- Pannello laterale fisso con floating button "💬"
- Pulse animation quando il chatter è attivo
- Apertura automatica al primo run

### 12. Nessuna onboarding
Primo accesso: board vuota, nessuna guida.

**Suggerimenti:**
- Tour guidato al primo login (es. shepherd.js)
- Issue di esempio pre-creata
- Tooltip sui pulsanti principali

### 13. Nessun undo/redo
Cancellazione e cambio status sono irreversibili (solo conferma dialog).

**Suggerimenti:**
- Snackbar "Undo" dopo delete (stile Gmail)
- Soft-delete con trash / cronologia modifiche

### 14. `confirm()` nativo per kill terminal
`if (!confirm("Terminare questo terminale?"))` — dialog brutto e fuori stile.

**Suggerimenti:**
- Usare Dialog Radix UI (come già fatto per delete issue)
- Aggiungere "Don't ask again" checkbox

### 15. Terminale sempre in tema scuro
Anche in light mode, il terminale usa tema catppuccin scuro.

**Suggerimenti:**
- Tema chiaro per light mode (catppuccin latte vs mocha)
- Preferenza tema terminale salvata indipendentemente

---

## ⚡ Quick Wins (a basso sforzo, alto impatto)

| Priorità | Cosa | Sforzo | Impatto |
|----------|------|--------|---------|
| 🔴 | **Cmd+K global search + shortcut** | ~3gg | Altissimo |
| 🔴 | **Sidebar collassabile icon-only** | ~1gg | Molto alto |
| 🟡 | **Breadcrumb navigation** | ~0.5gg | Alto |
| 🟡 | **Bulk actions su Kanban** | ~2gg | Alto |
| 🟡 | **Empty state migliorati + onboarding** | ~1gg | Alto |
| 🟡 | **Quick-create issue dalla sidebar** | ~0.5gg | Alto |
| 🟢 | **Sostituire `confirm()` con Dialog Radix** | ~0.5gg | Medio |
| 🟢 | **Tema terminale coerente light/dark** | ~0.5gg | Medio |
| 🟢 | **Card con micro-animazioni hover** | ~0.5gg | Basso |
| 🟢 | **Dashboard con metriche** | ~2gg | Alto |

---

## 🏗️ Architettura — Ristrutturazioni Consigliate

### Sidebar Unification
Unire `ProjectSidebar` + `AppSidebar` in un unico pannello a 3 livelli:
1. **Icone globali** (Dashboard, Queue, Terminals, Agents, Settings, Providers)
2. **Lista progetti** (con expand/collapse, favoriti in alto)
3. **Pagine del progetto** (issues, files, memories, health, plugins, variables)

### Route Organization
11 sub-routes per progetto sono tante. Possibile raggruppamento:
- Raggruppare plugin/variables/commands sotto "Project Settings" dropdown
- Pipeline come sezione inline nell'issue invece che pagina separata
- Fondere `ask.tsx` in un floating button globale

### Stato UI Locale
React Query non è ideale per preferenze UI (sidebar collapse, filtri, tema terminale). Valutare **Zustand** o React Context per stato UI transiente.

---

## 📁 Struttura File Analizzata

```
src/
├── features/
│   ├── activity/        — Activity timeline + hooks
│   ├── agents/          — Agents tab
│   ├── conflicts/       — Conflict modals (import)
│   ├── files/           — File gallery + modals
│   ├── import/          — Import preview
│   ├── issues/          — Kanban, issue detail, actions (CORE)
│   ├── library/         — Skill library
│   ├── memories/        — Memory tree + search + detail
│   ├── pipeline-runs/   — PipelineProgress, AgentChat, LogViewer
│   ├── pipelines/       — Pipeline editor tab
│   ├── projects/        — Project CRUD, settings, health, dashboard
│   ├── providers/       — Provider configuration
│   ├── questions/       — Pending questions + cards
│   ├── queue/           — Global queue page
│   ├── settings/        — Settings form, plugins, Hermes integration
│   ├── system/          — System info API
│   └── terminals/       — Terminal panel, grid, action bar, dialogs
├── routes/              — TanStack Router pages (file-based)
├── shared/
│   ├── api/             — HTTP client (fetch wrapper)
│   ├── components/      — Sidebar, error boundary, markdown, speech, QR
│   │   └── ui/          — shadcn components (button, card, dialog, etc.)
│   ├── context/         — EventProvider (WebSocket)
│   ├── hooks/           — use-mobile, use-speech-recognition
│   ├── lib/             — query-client, utils (cn)
│   ├── types/           — TypeScript interfaces (Issue, Project, Task, etc.)
│   └── utils/           — download, saveFile
├── main.tsx             — Entry point
├── index.css            — Tailwind + CSS variables (light/dark)
└── routeTree.gen.ts     — Auto-generated route tree
```
