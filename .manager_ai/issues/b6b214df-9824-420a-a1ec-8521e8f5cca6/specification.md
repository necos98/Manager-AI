# Specifica: Sezione Hermes nei Settings con comandi eseguibili

## Panoramica

Aggiungere una sezione "Hermes" nella pagina Settings di Manager AI, contenente una lista di comandi CLI di Hermes Agent che l'utente può eseguire con un click. Cliccando il pulsante "Run" su un comando, si apre una modale con un terminale interattivo che esegue automaticamente il comando. Chiudendo la modale il terminale viene killato.

## Architettura

### Backend

**Storage**: I comandi Hermes vengono memorizzati come setting JSON nella tabella `settings`:
- **Key**: `hermes_commands`
- **Value**: JSON array di oggetti `{name, description, command}`
- **Default** (in default_settings.json):

```json
[
  {"name": "Verifica Connessione MCP", "description": "Testa la connessione MCP tra Manager AI e Hermes Agent", "command": "hermes mcp list"},
  {"name": "Lista Skill Hermes", "description": "Mostra le skill installate in Hermes Agent", "command": "hermes skills list"},
  {"name": "Stato Sessione Hermes", "description": "Mostra lo stato della sessione Hermes corrente", "command": "hermes status"}
]
```

**Nuovo endpoint**: `GET /api/settings/hermes-commands` — restituisce il JSON parsato dei comandi (array). Opzionale, ma rende il frontend più pulito. In alternativa, il frontend può leggere direttamente il setting con `fetchSettings()` e filtrarlo per chiave.

### Frontend

**Struttura**:
1. Aggiungere `"Hermes"` all'array `TABS` in `settings.tsx`
2. Creare un nuovo componente `HermesCommandsPanel` (inline in `settings.tsx` o in un nuovo file in `features/settings/components/`)
3. Ogni comando nella lista mostra: nome, descrizione, pulsante "Run"
4. Il click su "Run" crea un terminale via `useCreateTerminal` con `issue_id=""` e `command` impostato, poi apre un Dialog contenente `TerminalPanel`
5. Alla chiusura del Dialog, killare il terminale

**Flusso interazione**:
1. Settings page → tab "Hermes" → lista comandi
2. Click "Run" → `createTerminal.mutateAsync({project_id: "", issue_id: "", command: "hermes ..."})` crea PTY
3. Il terminale auto-scrive il comando (grazie al campo `command` in `TerminalCreate`)
4. Il Dialog si apre mostrando TerminalPanel collegato al terminalId
5. L'utente interagisce col terminale (comando interattivo)
6. Chiudendo il Dialog → `killTerminal` → terminale killato

**Stato terminalId**: gestito via useState<string | null> — se null, il Dialog è chiuso; se valorizzato, il Dialog è aperto con il terminale.

## Dettagli implementativi

### Backend

1. **default_settings.json** — Aggiungere entry `hermes_commands` con valore JSON predefinito e descrizione.
2. **settings.py router** — Opzionale: aggiungere endpoint `GET /settings/hermes-commands` che ritorna il JSON decodificato.

### Frontend (settings.tsx)

1. Aggiungere `"Hermes"` a `TABS` array
2. Nel tab Hermes, filtrare settings per trovare `hermes_commands` key
3. Parsare il JSON e renderizzare la lista
4. Stato `activeTerminalId: string | null` per tracciare il terminale aperto nel Dialog
5. Stato `activeCommandName: string | null` per il titolo del Dialog
6. Al click "Run": chiamare `createTerminal.mutateAsync({project_id: "", issue_id: "", command: commandText})`
7. Al successo: `setActiveTerminalId(terminal.id)` e `setActiveCommandName(command.name)`
8. Dialog contiene TerminalPanel con terminalId, projectId vuoto
9. OnOpenChange(false): killare terminale via `killTerminal.mutateAsync(activeTerminalId)` e resettare stato

## Vincoli

- I comandi devono essere espandibili: basta modificare il setting `hermes_commands` per aggiungerne di nuovi
- La modale usa lo stesso pattern di AgentsTab (Dialog + TerminalPanel)
- Il terminale deve essere interattivo (PTY, non log terminal)
- project_id="" e issue_id="" perché i comandi sono operazioni di sistema, non legate a un progetto/issue specifico
- Alla chiusura della modale, il terminale viene killato (non lasciare zombie)