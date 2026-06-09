## Specifica: Errore console all'apertura terminale nella sezione Settings

### Problema
Quando si apre un terminale nella sezione Settings → Hermes (tramite il pulsante "Run" su un comando Hermes), si verifica un errore visibile nella console del browser/devtools. L'errore è intermittente e si manifesta più frequentemente quando il comando Hermes termina rapidamente (es. `hermes skills list`).

### Root cause identificata

**Race condition nel lifecycle del Dialog + TerminalPanel**

Il componente `HermesCommandsPanel` in `routes/settings.tsx` ha due percorsi distinti per la chiusura del terminale:

1. **Chiusura naturale** (comando Hermes termina): `handleSessionEnd()` → setActiveTerminalId(null) + setActiveDialogOpen(false)
2. **Chiusura manuale** (utente clicca X/fuori): `handleDialogClose(false)` → killTerminal + setActiveTerminalId(null)

Quando il comando Hermes termina rapidamente:
- `handleSessionEnd` chiude dialog e cancella terminalId
- Durante l'animazione di chiusura del Dialog, React potrebbe triggerare `onOpenChange(false)` → `handleDialogClose` tenta di fare `killTerminal` su activeTerminalId ora null

Questo causa: **Cannot read properties of null (reading 'id')** o **TypeError: terminalId is null** nella console.

Ulteriore problema: quando `handleSessionEnd` e `handleDialogClose` si sovrappongono, `killTerminal.mutate(activeTerminalId)` con activeTerminalId già null bypassa il guard `if (!open && activeTerminalId)` a causa di **stale closure** — React Query batching mantiene activeTerminalId ancora non null nel closure della mutation al momento dell'invocazione.

### Sintomi
- TypeError: terminalId is null / Cannot read properties of null
- A volte: `QueryCache.onError` o errori React su state update dopo unmount
- Il terminale si apre, mostra brevemente l'output, poi errore in console

### Fix proposti

#### Fix 1: useRef per tracciare lo stato del terminale
Sostituire la dipendenza dal closure `activeTerminalId` con una `useRef` per evitare stale closure in `handleDialogClose`.

#### Fix 2: Guard esplicito in handleDialogClose
Aggiungere controllo `if (activeTerminalIdRef.current)` prima di killTerminal, usando il ref anziché lo state.

#### Fix 3: Sync handleSessionEnd per evitare doppia chiusura
In `handleSessionEnd`, pulire il ref PRIMA di settare gli state, così `handleDialogClose` vede subito il ref nullo e non tenta kill.

### Non obiettivo
- Non modificare `TerminalPanel` (funziona correttamente negli altri contesti)
- Non modificare il backend
- Non aggiungere logica di retry o riconnessione

### Criteri di accettazione
- AC1: Nessun errore JS in console all'apertura del terminale in Settings→Hermes
- AC2: Nessun errore JS in console alla chiusura naturale del terminale (comando completato)
- AC3: Nessun errore JS in console alla chiusura manuale del terminale (click X / fuori dialog)
- AC4: Terminale funziona correttamente in tutti gli scenari (comando lungo, corto, chiusura manuale)
