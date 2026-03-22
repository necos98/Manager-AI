# Manager AI — Roadmap

Ultimo aggiornamento: 2026-03-22

---

## Fase 0 — Consolidamento (Completata)

Workflow hardening: state machine corretta, service layer unificato, hook firing consistente.

- [x] Custom exception hierarchy (`AppError`, `NotFoundError`, `InvalidTransitionError`, `ValidationError`)
- [x] Global exception handler in FastAPI
- [x] Rimozione stato DECLINED, aggiunta transizione NEW → REASONING
- [x] Migrazione issue service a eccezioni custom
- [x] Hook firing nel service layer (REST e MCP consistenti)
- [x] MCP tools semplificati a thin wrappers
- [x] Router senza business logic
- [x] Enforcement completamento task prima di FINISHED
- [x] Logging nel hook system
- [x] Validazione input (recap non vuoto, nome max 500 char)
- [x] Terminal cleanup alla cancellazione progetto

---

## Fase 1 — Allineamento Architetturale

Completare il pattern stabilito in Fase 0 su tutto il codebase.

### 1.1 ProjectService allineato al pattern
- [ ] `get_by_id()` lancia `NotFoundError` invece di ritornare `None`
- [ ] Router projects senza try/except manuali (usa global handler)
- [ ] `update_project_context` MCP tool passa per il service layer
- [ ] Fix dei 3 test pre-esistenti (`test_get_project_not_found`, `test_settings_service`, `test_routers_settings`)

### 1.2 Pulizia MCP tool descriptions
- [ ] Aggiungere descrizione della state machine (NEW → REASONING → PLANNED → ACCEPTED → FINISHED) nelle tool descriptions
- [ ] Documentare l'ordine d'uso dei tool (`create_issue_spec` → `create_issue_plan` → `accept_issue` → `complete_issue`)
- [ ] Chiarire quando usare `send_notification` vs completare silenziosamente

### 1.3 Import cleanup
- [ ] Spostare import lazy di `TaskService`/`TaskStatus` in `complete_issue()` a livello di modulo (risolvere circular dependency)
- [ ] Standardizzare `except Exception` in MCP task tools a `except AppError`

---

## Fase 2 — UI Interattiva

Oggi la UI è read-only per lo stato delle issue. L'utente non può interagire con il workflow dal browser.

### 2.1 Controllo stato issue dal frontend
- [ ] Bottoni di transizione stato in IssueDetailPage basati sullo stato corrente:
  - NEW: "Avvia Analisi" (→ triggera Claude per spec)
  - PLANNED: "Accetta Piano" / "Richiedi Modifiche"
  - ACCEPTED: "Segna come Completata" (con validazione task)
  - Qualsiasi stato: "Cancella Issue"
- [ ] Modale di conferma per ogni transizione
- [ ] StatusBadge cliccabile con dropdown delle transizioni valide

### 2.2 Feedback inline sul piano
- [ ] Campo di testo in IssueDetailPage quando lo stato è PLANNED: "Dai feedback a Claude"
- [ ] Il feedback viene salvato e Claude lo riceve come contesto per `edit_issue_plan`
- [ ] Storico dei feedback visibile nella timeline dell'issue

### 2.3 Task management dalla UI
- [ ] Lista task editabile in IssueDetailPage (non solo read-only badges)
- [ ] Checkbox per marcare task come completati
- [ ] Aggiunta/rimozione task manuali
- [ ] Drag-and-drop per riordinare

### 2.4 Editing inline
- [ ] Modifica priorità issue dal detail page
- [ ] Modifica descrizione issue
- [ ] Modifica nome issue

---

## Fase 3 — Real-Time & Auto-Refresh

Il frontend carica i dati una volta e non si aggiorna. Quando Claude lavora via MCP, l'utente vede dati stale.

### 3.1 Event-driven data refresh
- [ ] Emettere eventi WebSocket per ogni cambio stato issue (`issue_status_changed`)
- [ ] Emettere eventi per aggiornamento task (`task_updated`)
- [ ] Emettere eventi per nuova spec/piano/recap (`issue_content_updated`)
- [ ] EventContext aggiorna i dati delle pagine oltre a mostrare toast:
  - IssueDetailPage si refresha quando riceve eventi per quell'issue
  - ProjectDetailPage si refresha quando riceve eventi per quel progetto

### 3.2 Toast tipizzati
- [ ] Tipi di toast: info (blu), success (verde), warning (giallo), error (rosso)
- [ ] `hook_failed` → toast rosso
- [ ] `hook_completed` → toast verde
- [ ] `notification` → toast blu
- [ ] Toggle suono nelle settings

### 3.3 Activity log persistente
- [ ] Modello `ActivityLog` nel DB: timestamp, tipo evento, issue_id, project_id, dettagli
- [ ] Ogni transizione di stato, hook, notifica viene loggata
- [ ] Pagina o sezione "Activity" nel frontend con timeline scrollabile
- [ ] Filtro per progetto/issue

---

## Fase 4 — Automazione del Workflow

Il salto di qualità: da "issue tracker con terminale" a "AI project manager che lavora per te".

### 4.1 Auto-start workflow
- [ ] Nuovo `HookEvent.ISSUE_CREATED`
- [ ] Hook `AutoStartSpecification`: alla creazione di un'issue, spawna automaticamente Claude Code che:
  1. Legge la descrizione dell'issue
  2. Scrive la specification (`create_issue_spec`)
  3. Scrive il piano (`create_issue_plan`)
  4. Crea i task atomici (`create_plan_tasks`)
  5. Notifica l'utente ("Piano pronto per review")
- [ ] Configurabile per progetto: on/off, prompt template custom
- [ ] Timeout e gestione errori (se Claude fallisce, issue resta in NEW con errore loggato)

### 4.2 Auto-start implementazione
- [ ] Quando l'utente accetta un piano (PLANNED → ACCEPTED), automaticamente:
  1. Apre un terminale per l'issue
  2. Lancia Claude Code con il piano come contesto
  3. Claude implementa task per task, aggiornando lo stato
  4. Al completamento, chiama `complete_issue` con recap
- [ ] Monitoraggio progresso via task status in real-time
- [ ] Possibilità di interrompere ("Fermati e aspetta istruzioni")

### 4.3 Auto-completion detection
- [ ] Quando tutti i task di un'issue sono COMPLETED, suggerisci automaticamente il completamento
- [ ] Opzione: auto-complete con recap generato da Claude
- [ ] Opzione: notifica utente per review finale prima del complete

### 4.4 Coda di lavoro
- [ ] `get_next_issue` usato per processare issue in ordine di priorità
- [ ] Workflow continuo: finita un'issue, parte la prossima
- [ ] Dashboard "Claude sta lavorando su..." con progresso in tempo reale
- [ ] Pausa/resume della coda

---

## Fase 5 — Prompt & Template System

Rendere i prompt configurabili senza toccare codice.

### 5.1 Prompt template per progetto
- [ ] Modello `PromptTemplate`: project_id, tipo (spec, plan, recap, enrich), contenuto
- [ ] Template default globali, override per progetto
- [ ] Variabili nei template: `{{issue_description}}`, `{{project_context}}`, `{{tech_stack}}`
- [ ] UI per editing template nella pagina progetto

### 5.2 System prompt per Claude Code
- [ ] Configurazione del system prompt iniettato quando Claude lavora su un progetto
- [ ] Include: regole di stile, pattern architetturali, convenzioni naming, istruzioni specifiche
- [ ] Integrazione con `.claude/CLAUDE.md` del progetto target

### 5.3 MCP tool description configurabili
- [ ] Le descrizioni dei tool MCP diventano template
- [ ] Possibilità di personalizzare per progetto cosa Claude vede come istruzioni dei tool
- [ ] Es: per un progetto Python, `create_issue_plan` include "usa pytest per i test"

---

## Fase 6 — Terminale Avanzato

### 6.1 Shell configurabile
- [ ] Supporto PowerShell, Git Bash, WSL oltre a cmd.exe
- [ ] Configurazione shell per progetto
- [ ] Variabile d'ambiente `MANAGER_AI_SHELL` già supportata, esporre nella UI

### 6.2 Variabili template estese
- [ ] Variabili custom definibili per progetto (es: `$db_url`, `$api_key`)
- [ ] Secrets management: variabili sensibili non mostrate in chiaro nella UI
- [ ] Variabili d'ambiente aggiuntive iniettabili nel terminale

### 6.3 Terminal UX migliorata
- [ ] Ricerca nel buffer di output (Ctrl+F)
- [ ] Copia/incolla con bottoni
- [ ] Temi terminale configurabili
- [ ] Split pane: due terminali affiancati per la stessa issue
- [ ] Session recording: salvare l'output di un terminale per review futura

### 6.4 Terminal commands avanzati
- [ ] Sintassi multi-linea per i comandi di startup
- [ ] Condizioni: "esegui questo comando solo se $issue_status == ACCEPTED"
- [ ] Template di comandi predefiniti: "Setup Python venv", "Install deps + run tests"
- [ ] Validazione sintassi dei comandi prima del salvataggio

---

## Fase 7 — Multi-Issue & Orchestrazione

### 7.1 Dashboard avanzata
- [ ] Vista Kanban delle issue (colonne per stato)
- [ ] Drag-and-drop per cambiare stato
- [ ] Filtri: priorità, data creazione, nome
- [ ] Ricerca full-text nelle issue (descrizione, spec, piano)

### 7.2 Issue collegate
- [ ] Relazioni tra issue: "blocca", "bloccata da", "correlata a"
- [ ] Visualizzazione grafo delle dipendenze
- [ ] Claude non può iniziare un'issue se le sue dipendenze non sono FINISHED

### 7.3 Multi-project view
- [ ] Dashboard globale: tutte le issue attive cross-progetto
- [ ] Statistiche: issue completate per settimana, tempo medio per issue
- [ ] Timeline globale di attività

### 7.4 Lavoro parallelo
- [ ] Supporto per più issue in lavorazione contemporaneamente
- [ ] Terminali multipli visibili in layout a griglia
- [ ] Context switching rapido tra issue

---

## Fase 8 — Verso il Framework (Direzione C)

Per rendere Manager AI usabile da altri sviluppatori.

### 8.1 Plugin architecture
- [ ] Hook definibili come plugin (Python packages installabili)
- [ ] Hook configurabili da UI senza scrivere codice
- [ ] Marketplace di hook community: "auto-deploy", "run tests", "notify Slack"

### 8.2 MCP tool personalizzati per progetto
- [ ] Ogni progetto può esporre tool MCP aggiuntivi
- [ ] Es: progetto backend espone "run_migrations", progetto frontend espone "build_storybook"
- [ ] Tool definiti come script nella cartella del progetto

### 8.3 Project templates
- [ ] Template preconfigurati: "Python Backend", "React Frontend", "Full-Stack", "Data Pipeline"
- [ ] Ogni template include: terminal commands, hook, prompt templates, settings
- [ ] Creazione progetto da template con un click

### 8.4 File system avanzato
- [ ] Preview inline per PDF, immagini, markdown
- [ ] Link file a issue specifiche (allegati per issue)
- [ ] Supporto file immagine (PNG, JPG, SVG)
- [ ] Versionamento dei file (storico upload)

### 8.5 Documentazione e onboarding
- [ ] Documentazione completa delle API
- [ ] Guida "Getting Started" per nuovi utenti
- [ ] Video walkthrough del workflow
- [ ] Contribuire: guida per sviluppatori che vogliono estendere Manager AI

---

## Priorità Raccomandata

| Priorità | Fase | Impatto | Effort |
|----------|------|---------|--------|
| 1 | 1 — Allineamento architetturale | Medio | Basso |
| 2 | 2.1 — Controllo stato dalla UI | Alto | Medio |
| 3 | 3.1 — Event-driven refresh | Alto | Medio |
| 4 | 4.1 — Auto-start workflow | Altissimo | Alto |
| 5 | 2.3 — Task management dalla UI | Alto | Medio |
| 6 | 4.2 — Auto-start implementazione | Altissimo | Alto |
| 7 | 3.3 — Activity log | Medio | Medio |
| 8 | 5.1 — Prompt templates | Alto | Medio |
| 9 | 7.1 — Dashboard Kanban | Alto | Alto |
| 10 | 6.1-6.4 — Terminale avanzato | Medio | Alto |
