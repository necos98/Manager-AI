# Fase 6 — Terminale Avanzato

## Obiettivo

Portare il terminale integrato da strumento base a strumento configurabile e produttivo: shell per progetto, variabili d'ambiente custom, UX migliorata e comandi di avvio avanzati.

---

## Cosa è stato implementato

### 6.1 Shell configurabile per progetto

- Nuova colonna `project.shell` (nullable) — migration `aa1bb2cc3dd4`
- `TerminalService.create()` accetta `shell` opzionale; se non specificato usa `MANAGER_AI_SHELL` env o il default di sistema
- Selector nella dialog "Edit Project" con 8 opzioni: Default, cmd.exe, PowerShell, pwsh, Git Bash, WSL, bash, zsh
- Rimossa la deduplicazione per `issue_id` nel service (prerequisito per lo split pane)

### 6.2 Variabili custom di progetto

- Nuova tabella `project_variables` con `name`, `value`, `is_secret`, `sort_order` — migration `bb2cc3dd4ee5`
- `ProjectVariableService` — CRUD con gestione duplicati e cascade delete
- Router `/project-variables` (GET, POST, PUT, DELETE)
- Le variabili vengono iniettate nel terminale come `set VAR=value` (Windows) o `export VAR=value` (Unix) all'apertura
- Pagina `/projects/:id/variables` con editor inline: blur-to-save, reveal toggle per i secret, link in sidebar

### 6.3 UX terminale migliorata

| Feature | Dettaglio |
|---|---|
| **Ricerca** | Ctrl+F apre search bar, Enter/Shift+Enter per next/prev, Esc per chiudere — usa `@xterm/addon-search` |
| **Copia** | Toolbar con bottone Copy che legge `term.getSelection()` |
| **Temi** | 4 temi configurabili globalmente: Catppuccin, Dracula, One Dark, Solarized Dark. Aggiornamento live senza ricreare il terminale |
| **Split pane** | Fino a 2 terminali per issue in layout verticale resizable. Bottone "Split" quando è aperto 1 terminale, "Close All" quando sono 2 |
| **Session recording** | Buffer salvato in `data/recordings/{id}.txt` alla chiusura (naturale o forzata). Endpoint `GET /terminals/{id}/recording` per il download, con bottone nella toolbar |

### 6.4 Comandi di startup avanzati

- Nuova colonna `terminal_commands.condition` (nullable TEXT) — migration `cc3dd4ee5ff6`
- **Multi-linea**: un comando può contenere `\n`, ogni riga viene inviata al PTY separatamente
- **Condizioni**: sintassi `$issue_status == ACCEPTED` — il comando viene eseguito solo se la condizione è vera
- **Template predefiniti**: endpoint `GET /terminal-commands/templates` con 5 template (Python venv, Node install+test, Run tests, Git status, Docker build)
- **Frontend**: editor con `Textarea` (invece di `Input`), campo condizione per ogni comando, dropdown Templates che precompila il form

---

## Schema delle migration

```
de00ebdfc1c2  (pre-esistente)
    └── aa1bb2cc3dd4  add project.shell
            └── bb2cc3dd4ee5  add project_variables table
                    └── cc3dd4ee5ff6  add terminal_commands.condition
```

---

## File principali

| Area | File |
|---|---|
| Backend models | `models/project_variable.py`, `models/project.py`, `models/terminal_command.py` |
| Backend services | `services/project_variable_service.py`, `services/terminal_command_service.py`, `services/terminal_service.py` |
| Backend routers | `routers/project_variables.py`, `routers/terminals.py`, `routers/terminal_commands.py` |
| Frontend components | `terminals/components/terminal-panel.tsx`, `terminals/components/terminal-commands-editor.tsx`, `projects/components/project-variables-editor.tsx` |
| Frontend route | `routes/projects/$projectId/variables.tsx` |
| Frontend temi | `terminals/themes.ts` |
