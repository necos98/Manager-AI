# Piano: Sezione Hermes nei Settings con comandi eseguibili

## Approccio

La sezione "Hermes" nei Settings mostra una lista di comandi CLI che l'utente può eseguire. I comandi sono memorizzati come setting JSON (`hermes_commands`) nella tabella settings, espandibile modificando il setting. 

Per i terminali Hermes, serve un nuovo endpoint backend dedicato (similarmente a manage-agent terminal) che non richiede un project_id valido. Il frontend legge i comandi dall'API settings, e per eseguirli crea un terminale via API e apre una modale con TerminalPanel.

## Task

### Task 1: Backend — default setting `hermes_commands`
Aggiungere la entry `hermes_commands` in `default_settings.json` con valore JSON predefinito e descrizione.

### Task 2: Backend — endpoint `POST /terminals/hermes`
Nuovo endpoint in `terminals.py` e `terminal_operations.py`:
- `HermesTerminalCreate` schema con campo `command: str`
- `create_hermes_terminal()`: crea PTY con project_path derivato (come manage-agent), scrive il comando nel PTY
- Registrato PRIMA delle route /{terminal_id}

### Task 3: Frontend — hook e API per Hermes commands
Aggiungere in `settings/api.ts` la funzione `fetchHermesCommands()` e in `settings/hooks.ts` il relativo hook `useHermesCommands()`.

### Task 4: Frontend — Hermes tab + command list + terminal modal
In `settings.tsx`:
- Aggiungere "Hermes" a TABS
- Nuovo componente `HermesCommandsPanel`:
  - Legge `hermes_commands` via `useHermesCommands()`
  - Mostra lista con nome, descrizione, pulsante "Run"
  - Click "Run" → `createHermesTerminal` → apre Dialog con TerminalPanel
  - Chiusura Dialog → kill terminale

Tutti i task sono sequenziali (Task 1 → 2 → 3 → 4).