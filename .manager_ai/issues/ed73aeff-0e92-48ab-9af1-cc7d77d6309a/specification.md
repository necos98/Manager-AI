## Quick Create Issue dalla Sidebar

### Problema
Attualmente il pulsante "New Issue" è visibile solo nella pagina Issues del progetto, costringendo l'utente a navigare lì per creare una nuova issue — interruzione del flusso di lavoro.

### Soluzione Proposta
Aggiungere un pulsante "+" accanto a ogni progetto nella ProjectSidebar che apre una **QuickCreateDialog** — una versione ridotta del modal di creazione con solo i campi essenziali (descrizione + priorità).

### Componenti da creare/modificare

**1. QuickCreateIssueDialog (nuovo componente)**
- Path: `frontend/src/features/issues/components/quick-create-issue-dialog.tsx`
- Dialog leggero con solo:
  - Textarea per la descrizione
  - Priority select (dropdown, default 3)
  - Pulsante Create (con stato loading)
  - Pulsante Cancel
- Nessun campo Tags, Category, Browse Files, Voice
- Nessun abandon-confirmation (troppo pesante per un quick create)
- Submit via Ctrl+Enter o click Create
- Reset del form alla chiusura
- Riutilizza `useCreateIssue` hook già esistente
- Su successo: toast "Issue created", chiusura dialog

**2. ProjectSidebarItem — pulsante "+"**
- File: `frontend/src/shared/components/project-sidebar.tsx`
- Aggiungere un SidebarMenuAction "+" (o icona Plus) accanto a ogni progetto
- Il pulsante appare al click o come icona sempre visibile accanto allo star/favorite
- Al click: apre QuickCreateIssueDialog per quel progetto
- Stile minimal, coerente con lo star già esistente

**3. Keyboard shortcut (opzionale, secondaria)**
- Shortcut `n` globale per aprire QuickCreateDialog del progetto attivo
- Da valutare se implementare subito o come miglioramento futuro

### Flusso utente
1. L'utente vede l'icona "+" accanto al progetto nella sidebar
2. Click → si apre il quick create dialog (sovrapposto, non naviga via)
3. Scrive descrizione, sceglie priorità, click Create
4. Toast di conferma, dialog si chiude
5. L'utente rimane dov'era — nessuna navigazione

### Pattern UI esistenti da seguire
- Usa `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogFooter` da `@/shared/components/ui/dialog`
- Usa `Textarea` da `@/shared/components/ui/textarea`
- Usa `Select` da `@/shared/components/ui/select`
- Usa `Button` da `@/shared/components/ui/button`
- Stile coerente con NewIssueDialog ma più compatto (senza sezioni tags/category/files/voice)
- Icona Plus da lucide-react, già importata nel progetto

### Vincoli
- Non modificare la NewIssueDialog esistente (viene usata per creazione avanzata)
- Il componente deve funzionare con projectId passato come prop
- Il pulsante "+" nella sidebar deve essere accessibile via tooltip
