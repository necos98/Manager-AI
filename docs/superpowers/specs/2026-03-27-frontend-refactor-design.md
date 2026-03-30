# Frontend Refactor Design Spec

**Date:** 2026-03-27
**Scope:** Complete frontend rewrite — JS to TypeScript, new routing/state/UI stack, modernized UI

## 1. Stack Tecnologico

- **TypeScript** strict mode
- **React 19** + **Vite 8**
- **TanStack Router** (file-based routing)
- **TanStack Query** (server state, caching, mutations)
- **shadcn/ui** + **Tailwind CSS v4** (componenti UI)
- **Radix UI** (primitivi accessibili, usati da shadcn)
- **xterm.js** (terminale — mantenuto)
- **react-markdown** (rendering markdown — mantenuto)
- **lucide-react** (icone, richiesto da shadcn)
- **sonner** (toast notifications, integrato con shadcn)

Nessun state manager globale aggiuntivo. TanStack Query gestisce lo stato server, React context solo per WebSocket/eventi.

## 2. Strategia di Migrazione

**Big bang** — riscrittura completa del frontend. Il progetto e' ~2000 righe su 19 file, abbastanza contenuto per una sostituzione totale. Il frontend JS attuale viene rimosso e sostituito interamente.

## 3. Struttura Cartelle

```
src/
├── main.tsx                          # Entry point
├── index.css                         # Tailwind imports + shadcn theme
├── routeTree.gen.ts                  # Auto-generato da TanStack Router
│
├── routes/                           # TanStack Router file-based routes
│   ├── __root.tsx                    # Root layout (sidebar + event provider)
│   ├── index.tsx                     # / → se esiste un solo progetto, redirect a quello; altrimenti lista progetti
│   ├── settings.tsx                  # /settings
│   └── projects/
│       ├── $projectId.tsx            # Layout progetto (contestualizza sidebar)
│       └── $projectId/
│           ├── issues.tsx            # /projects/$projectId/issues (lista issues)
│           ├── issues/
│           │   ├── new.tsx           # /projects/$projectId/issues/new
│           │   └── $issueId.tsx      # /projects/$projectId/issues/$issueId (detail + terminal)
│           ├── files.tsx             # /projects/$projectId/files
│           └── commands.tsx          # /projects/$projectId/commands (terminal commands)
│
├── features/
│   ├── projects/
│   │   ├── api.ts                    # Query/mutation functions
│   │   ├── hooks.ts                  # useProjects, useProject, useCreateProject, etc.
│   │   ├── components/
│   │   │   ├── project-switcher.tsx  # Dropdown selezione progetto nella sidebar
│   │   │   └── project-settings-dialog.tsx
│   │   └── types.ts                 # Tipi TypeScript per Project
│   │
│   ├── issues/
│   │   ├── api.ts
│   │   ├── hooks.ts                  # useIssues, useIssue, useCreateIssue, useUpdateStatus
│   │   ├── components/
│   │   │   ├── issue-list.tsx        # Lista issues con filtri
│   │   │   ├── issue-detail.tsx      # Contenuto scrollabile dell'issue
│   │   │   ├── issue-form.tsx        # Form creazione/modifica (riuso)
│   │   │   ├── status-badge.tsx
│   │   │   └── task-list.tsx         # Lista task del piano
│   │   └── types.ts
│   │
│   ├── terminals/
│   │   ├── api.ts
│   │   ├── hooks.ts                  # useTerminals, useCreateTerminal, useKillTerminal
│   │   ├── components/
│   │   │   ├── terminal-panel.tsx    # XTerm con WebSocket
│   │   │   └── terminal-commands-editor.tsx
│   │   └── types.ts
│   │
│   ├── files/
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   │   └── file-gallery.tsx
│   │   └── types.ts
│   │
│   └── settings/
│       ├── api.ts
│       ├── hooks.ts
│       ├── components/
│       │   └── settings-form.tsx
│       └── types.ts
│
├── shared/
│   ├── api/
│   │   └── client.ts                # Fetch wrapper tipizzato
│   ├── components/
│   │   ├── ui/                      # Componenti shadcn generati
│   │   ├── sidebar.tsx              # Sidebar layout con navigazione
│   │   ├── markdown-viewer.tsx
│   │   └── page-header.tsx          # Header riutilizzabile
│   ├── context/
│   │   └── event-context.tsx        # WebSocket events + invalidazione query + toast (sonner)
│   ├── hooks/
│   │   └── use-active-project.ts    # Hook per progetto attivo corrente
│   ├── lib/
│   │   └── utils.ts                 # cn() helper + utility varie
│   └── types/
│       └── index.ts                 # Tipi condivisi (enums, status, etc.)
```

## 4. Layout e Navigazione

### Layout Globale

```
┌──────────────────────────────────────────────────────┐
│ ┌─────────┐ ┌─────────────────────────────────────┐  │
│ │ Sidebar │ │         Content Area                │  │
│ │  (240px)│ │         (flex-1, scrollable)        │  │
│ │         │ │                                     │  │
│ │ Project │ │                                     │  │
│ │ Switcher│ │                                     │  │
│ │ ─────── │ │                                     │  │
│ │ Issues  │ │                                     │  │
│ │ Files   │ │                                     │  │
│ │Commands │ │                                     │  │
│ │ ─────── │ │                                     │  │
│ │Terminals│ │                                     │  │
│ │ Settings│ │                                     │  │
│ └─────────┘ └─────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

- **Sidebar fissa a sinistra (240px):** project switcher in alto, navigazione contestuale (Issues, Files, Terminal Commands), separatore, navigazione globale (Terminals con badge count, Settings).
- **Content area:** flex-1, contenuto specifico della route.
- **Stile Linear:** minimalista, spazio bianco, icone lucide, transizioni fluide.

### Layout Issue Detail (Split View)

```
┌─────────┬────────────────────────┬──────────────────┐
│         │   Issue Content        │    Terminal       │
│ Sidebar │   (scrollable)         │    (fixed right)  │
│         │                        │                   │
│         │  Title, Status, Badge  │   ┌────────────┐ │
│         │  Priority, Actions     │   │            │ │
│         │  ──────────────────    │   │  XTerm     │ │
│         │  Description           │   │            │ │
│         │  Specification         │   │            │ │
│         │  Plan + Tasks          │   │            │ │
│         │  Recap                 │   │            │ │
│         │                        │   └────────────┘ │
│         │                        │  [Kill] [New]    │
└─────────┴────────────────────────┴──────────────────┘
```

- Pannello terminale a destra (~40% content area), resizable con drag handle via shadcn `ResizablePanelGroup`
- Contenuto issue nel pannello sinistro in `ScrollArea`, scorre indipendentemente
- Se nessun terminale attivo: bottone "Open Terminal" nel pannello destro
- Pannello terminale visibile solo nella pagina issue detail

## 5. Data Flow e State Management

### TanStack Query — Server State

**Query keys gerarchiche:**
- `['projects']` → lista progetti
- `['projects', projectId]` → singolo progetto
- `['projects', projectId, 'issues']` → issues del progetto
- `['projects', projectId, 'issues', issueId]` → singola issue
- `['projects', projectId, 'issues', issueId, 'tasks']` → tasks dell'issue
- `['terminals']` → lista terminali
- `['terminals', 'count']` → conteggio (sidebar badge)
- `['settings']` → settings globali

**Comportamenti:**
- Mutations invalidano query correlate automaticamente
- Stale time: 30 secondi di default
- Polling: `['terminals', 'count']` ogni 5 secondi per badge sidebar
- Optimistic updates per azioni rapide (cambio status issue)

### React Context — Solo WebSocket/Eventi

- `EventContext` mantiene WebSocket a `/api/events/ws`
- Toast via `sonner` (sostituisce ToastContainer custom)
- Novita': eventi WebSocket invalidano query TanStack correlate → aggiornamento real-time automatico

### Nessun altro stato globale

Tutto il resto e' locale ai componenti (form state, UI toggles, etc.)

## 6. API Client e Tipizzazione

### Client base (`shared/api/client.ts`)

Funzione `request<T>()` generica tipizzata. Gestione errori centralizzata, Content-Type automatico (JSON vs FormData), ritorna tipo `T` parsato.

### API per feature (`features/*/api.ts`)

Funzioni tipizzate che usano il client base. Es:
- `fetchIssues(projectId: string): Promise<Issue[]>`
- `createIssue(projectId: string, data: CreateIssueInput): Promise<Issue>`

### Tipi (`features/*/types.ts`)

Derivati dagli schema Pydantic del backend. Es:
```typescript
type IssueStatus = 'new' | 'reasoning' | 'planned' | 'accepted' | 'declined' | 'finished'

interface Issue {
  id: number
  name: string | null
  description: string
  priority: number
  status: IssueStatus
  specification: string | null
  plan: string | null
  recap: string | null
  project_id: number
  created_at: string
  updated_at: string
}
```

### Hooks TanStack Query (`features/*/hooks.ts`)

Ogni hook wrappa query/mutation con key corrette e invalidazione automatica.

## 7. Gestione Terminale e WebSocket

- **TerminalPanel:** mantiene xterm.js + WebSocket bidirezionale (non TanStack Query)
- **FitAddon:** ricalcola su resize del pannello resizable
- **Stato terminale:** `useTerminals(projectId, issueId)` — mostra terminale attivo o bottone "Open Terminal"
- **EventContext:** WebSocket eventi chiama `queryClient.invalidateQueries` per aggiornamento real-time
- **Audio notifiche:** mantenuto, unlock al primo click utente

## 8. Componenti shadcn

| Componente | Uso |
|---|---|
| `button` | Azioni |
| `input` + `textarea` | Form fields |
| `select` | Project switcher, filtri, priority |
| `dialog` | Conferme delete, edit progetto |
| `dropdown-menu` | Azioni contestuali |
| `badge` | Status, priority, contatori |
| `card` | Container sezioni issue |
| `separator` | Divisori sidebar e sezioni |
| `scroll-area` | Scroll contenuto issue |
| `resizable` | Split view issue/terminale |
| `tooltip` | Hint su icone |
| `sonner` | Toast notifiche |
| `skeleton` | Loading states |
| `collapsible` | Sezioni collassabili issue detail |
| `tabs` | Dentro Settings se necessario |

**UI Patterns:**
- Skeleton durante caricamento, mai spinner generici
- Empty states con messaggio + CTA
- Error inline con retry button (da TanStack Query error state)
- Optimistic updates su azioni rapide

## 9. Deduplicazioni Codice

- **TerminalCommandsEditor:** oggi duplicato in ProjectDetailPage e SettingsPage → componente unico con prop `scope: "global" | "project"`
- **Setting fields:** 4 tab quasi identici in SettingsPage → componente `SettingField` riutilizzabile
- **Fetch pattern:** useState+useEffect duplicato in ogni pagina → eliminato da TanStack Query hooks
- **Form pattern:** form creazione issue e progetto → base condivisa con react-hook-form + validazione TS

## 10. Scope

### Incluso
- Migrazione completa 19 file JS → TypeScript
- React Router → TanStack Router (file-based)
- useState/useEffect fetch → TanStack Query
- Tailwind raw → shadcn/ui
- Struttura flat → feature-based
- ToastContainer custom → sonner
- Navbar → sidebar + project switcher
- Tab ProjectDetailPage → voci sidebar
- Issue detail tab terminale → split view terminale fisso a destra
- Deduplicazione codice

### Mantenuto
- xterm.js, react-markdown
- WebSocket per eventi e terminal I/O
- Vite come bundler
- Tailwind CSS (richiesto da shadcn)
- Tutte le funzionalita' esistenti

### Fuori scope
- Modifiche al backend
- Nuove funzionalita'
- Test frontend
