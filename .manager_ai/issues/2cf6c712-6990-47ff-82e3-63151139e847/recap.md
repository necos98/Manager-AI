# Recap: Sostituire confirm() nativo con Dialog Radix in terminals.tsx

## Modifica effettuata
Sostituito il confirm() nativo del browser in frontend/src/routes/terminals.tsx con un Dialog Radix UI, seguendo lo stesso pattern dei delete confirmation dialog già presenti in issue-detail.tsx e queue.tsx.

## Dettaglio modifiche
- Sostituito confirm() bloccante con stato confirmKillId: string | null
- handleKill(terminalId) ora apre il Dialog invece di chiamare confirm()
- Aggiunto doKill() che esegue killTerminal.mutate con onSuccess che chiude il dialog
- Aggiunto Dialog Radix con titolo, descrizione, Cancel (outline) e Terminate (destructive)
- Import aggiuntivi: useState, Button, Dialog components
- TypeScript compila senza errori (npx tsc --noEmit passa)

## File modificati
- frontend/src/routes/terminals.tsx (43 → 84 righe)