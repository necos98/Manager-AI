# Recap: Sezione Hermes nei Settings con comandi eseguibili

## Cosa è stato fatto

Creata una sezione "Hermes" nella pagina Settings di Manager AI.

### Backend
- **default_settings.json**: Aggiunto `hermes_commands` — setting JSON con 3 comandi predefiniti (Verifica Connessione MCP, Lista Skill Hermes, Stato Sessione Hermes)
- **Nuovo schema**: `HermesTerminalCreate` con campo `command: str` in `schemas/terminal.py`
- **Nuova operazione**: `create_hermes_terminal()` in `services/terminal_operations.py` — crea un PTY system-level (project_path derivato, senza project/issue), scrive il comando nel PTY
- **Nuova route**: `POST /api/terminals/hermes` in `routers/terminals.py`

### Frontend
- **Nuovo tipo**: `HermesCommand` in `shared/types/index.ts`
- **Nuova API**: `fetchHermesCommands()` in `settings/api.ts` — legge il setting JSON e lo parsifica
- **Nuovo hook**: `useHermesCommands()` in `settings/hooks.ts` — React Query wrapper
- **Nuovo hook**: `useCreateHermesTerminal()` in `terminals/hooks.ts` — per creare terminali Hermes
- **Settings page**: Tab "Hermes" aggiunto ai TABS con componente `HermesCommandsPanel`:
  - Lista comandi con nome, descrizione, comando in preformattato e pulsante "Run"
  - Click "Run" → crea terminale via `POST /terminals/hermes` → apre modale con TerminalPanel
  - Chiusura modale → kill del terminale

### Architettura
- Comandi espandibili: basta modificare il setting `hermes_commands` (JSON array)
- Terminali system-level con `project_id=""` e `issue_id=""` (come manage-agent)
- Pattern modale identico a AgentsTab (Dialog + TerminalPanel)