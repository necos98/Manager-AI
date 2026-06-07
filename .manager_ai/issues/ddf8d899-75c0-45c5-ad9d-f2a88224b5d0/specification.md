# Specifica: Export selettivo di Agenti e Pipeline con Save-As dialog

## Problema

1. Export Agenti/Pipeline solo "tutto" o "uno per volta" — nessun supporto export selettivo (multi-select)
2. Click export non mostra feedback — `downloadBlob()` crea `<a>` invisibile, nessuna indicazione all'utente
3. Utente non sa dove finisce il file — nessun Save-As dialog

## Requisiti

### R1 — Selezione multipla con checkbox
- Ogni riga agente e card pipeline mostra checkbox
- Intestazione colonna mostra checkbox "select all" (seleziona/deseleziona tutti)
- Contatore visivo: "N selected" nell'header della tabella/card grid
- Bottone "Export Selected" (disabilitato se 0 selezionati, mostra spinner durante export)

### R2 — Export batch (backend)
- Nuovo endpoint `POST /api/agents/export/batch` — accetta `{ agent_ids: string[] }` in body
- Nuovo endpoint `POST /api/pipelines/export/batch` — accetta `{ pipeline_ids: string[] }` in body
- Risposta: singolo file JSON con wrapper standard (`version`, `type`, `exported_at`, `items`)
- Stessa struttura esistente di `build_export_wrapper` — riutilizzare formatter esistenti
- Se lista ID vuota → 400 Bad Request
- Se ID inesistente → skip silenzioso (non fallisce tutto per un ID errato)

### R3 — Save-As dialog con fallback
- Usare `window.showSaveFilePicker()` (File System Access API) come primary
- Fallback: `downloadBlob()` esistente quando File System Access API non disponibile
- Nome file default: `agents-export.json` o `pipelines-export.json`
- Nessun cambiamento per export singolo esistente — funziona già

### R4 — Pipeline export include agenti annidati
- Già implementato backend-side (`format_pipeline_step_export` include `agent`)
- UI checkbox su pipeline seleziona tutto il nested agent automaticamente
- Nessuna modifica backend necessaria per questo aspetto

### R5 — Feedback utente durante export
- Stato loading su bottone "Export Selected" (spinner + disabilitato)
- Toast/notifica su successo: "Exported N agents/pipelines"
- Toast/notifica su errore: messaggio errore specifico

### R6 — Pagine separate
- Agenti e Pipeline sono pagine diverse (routes separate, tab diversi)
- Selezione checkbox è per-tab: selezioni su Agenti non influenzano Pipeline e viceversa

## Criteri di accettazione

1. Utente può selezionare N agenti con checkbox e fare export → file scaricato con solo quegli agenti
2. Utente può selezionare N pipeline con checkbox e fare export → file scaricato con quelle pipeline (inclusi agent annidati)
3. "Select all" seleziona/deseleziona tutti i checkbox visibili nella tabella/card grid corrente
4. Contatore "N selected" visibile e aggiornato in tempo reale
5. Bottone "Export Selected" disabilitato quando 0 selezionati
6. Export batch endpoint rifiuta body vuoto con 400
7. Save-As dialog appare su browser supportati (Chromium)
8. Fallback `downloadBlob()` su browser non supportati (Firefox, Safari)
9. Feedback visibile durante export (loading + notifica finale)
10. Export singolo esistente (icona per riga/card) continua a funzionare invariato

## Non-goals

- Non si modificano modelli dati (no nuove colonne/tabelle)
- Non si modifica la struttura del file di export (stesso JSON wrapper)
- Non si implementa export selettivo lato import (import già funziona con file completi)
- Non si aggiunge drag-and-drop o riordino
- Non si modifica l'import flow
- Non si aggiungono filtri o ricerca avanzata — solo checkbox

## Vincoli tecnici

- Frontend: React + TypeScript + TanStack Query — usare pattern esistenti (`useMutation`)
- Stessa `downloadBlob()` esistente come fallback — non duplicare, estrarre in shared utility
- UI esistenti: `AgentsTab.tsx` (tabella) e `PipelinesTab.tsx` (card grid)
- Backend: FastAPI + SQLAlchemy async — endpoint batch POST con lista ID in body