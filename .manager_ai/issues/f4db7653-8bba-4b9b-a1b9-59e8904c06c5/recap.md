## Recap: Errore console all'apertura terminale Settings

### Root cause
Race condition in `HermesCommandsPanel` (`routes/settings.tsx`) tra due percorsi di chiusura del terminale:
1. **Chiusura naturale**: `handleSessionEnd()` → setActiveTerminalId(null) + setActiveDialogOpen(false)
2. **Chiusura manuale**: `handleDialogClose(false)` → killTerminal + setActiveTerminalId(null)

Quando il comando Hermes termina rapidamente, `handleSessionEnd` chiude il dialog. Durante l'animazione di chiusura, React poteva triggerare `onOpenChange(false)` → `handleDialogClose` con `activeTerminalId` ancora non null nello stale closure, causando `TypeError: Cannot read properties of null`.

### Fix
Introdotto `useRef` (`activeTerminalIdRef`) per tracciare l'ID del terminale in modo sincrono:
- Il ref viene azzerato **prima** degli state update in `handleSessionEnd`
- `handleDialogClose` usa il ref (non lo state) come guard, eliminando stale closure
- `handleRun` aggiorna il ref insieme allo state

### File modificati
- `frontend/src/routes/settings.tsx` (HermesCommandsPanel): ~10 righe modificate