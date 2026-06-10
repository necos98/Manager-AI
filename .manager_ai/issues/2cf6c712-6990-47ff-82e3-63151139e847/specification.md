## Specifica: Sostituire confirm() nativo con Dialog Radix in terminals.tsx

### Stato attuale
Il file frontend/src/routes/terminals.tsx usa confirm() nativo del browser per chiedere conferma quando l'utente clicca Kill su un terminale attivo.

### Obiettivo
Sostituire confirm() con Dialog Radix UI, stesso pattern dei delete confirmation dialog in issue-detail.tsx e queue.tsx.

### Comportamento atteso
- Click Kill apre Radix Dialog
- Titolo: Terminate Terminal?
- Descrizione: Terminare questo terminale? I comandi in esecuzione verranno interrotti.
- Cancel (outline) chiude
- Terminate (destructive) esegue kill
- Disabilitato durante operazione con Terminating...
- Dismissibile overlay/Escape

### Implementazione
- Stato confirmKillId: string | null
- handleKill(terminalId) → setConfirmKillId(terminalId)
- doKill() → killTerminal.mutate(confirmKillId, { onSuccess: () => setConfirmKillId(null) })
- Dialog JSX dopo TerminalGrid