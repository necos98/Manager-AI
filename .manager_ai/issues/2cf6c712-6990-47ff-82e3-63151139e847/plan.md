# Piano: Sostituire confirm() nativo con Dialog Radix in terminals.tsx

## Modifiche
1 file da modificare: frontend/src/routes/terminals.tsx

## Passi
1. Aggiungere import useState, Button, Dialog components
2. Sostituire conferma nativa con stato confirmKillId e dialog Radix
3. Aggiungere Dialog JSX con titolo, descrizione, Cancel e Terminate buttons
4. Verificare compilazione TypeScript

## Implementazione già completata
Il codice è già stato implementato e verificato (npx tsc --noEmit passa senza errori).