## Issue: Export selettivo di Agenti e Pipeline con Save-As dialog

### Cosa è stato implementato
13 file modificati (5 backend, 8 frontend) per aggiungere export selettivo con checkbox e Save-As dialog.

### Backend
- Nuovi schemi `AgentBatchExportRequest`/`PipelineBatchExportRequest`
- `AgentService.export_batch()` e `PipelineService.export_batch()` — skip silenzioso ID inesistenti
- `POST /api/agents/export/batch` e `POST /api/pipelines/export/batch` — 400 se lista vuota

### Frontend
- Shared utility `downloadBlob()` estratta da codice duplicato
- Shared utility `saveFile()` con `showSaveFilePicker()` primario, fallback `downloadBlob()`
- AgentsTab: checkbox colonna, select-all con ref indeterminato, contatore "N selected", pulsante "Export Selected"
- PipelinesTab: checkbox su card, stessa logica di selezione
- Hooks batch con `saveFile()` + `toast.success()`

### Test
- 18/18 export/import test passati — nessuna regressione
- Pre-existing failures in project/dashboard/issue tests (non correlate)
- Batch endpoint non coperti da test (segnalato da QualityReviewer, fuori scope)

### Decisioni chiave
- POST con body JSON (non GET query params) per liste ID
- Silent skip ID inesistenti via SQL IN clause
- showSaveFilePicker primario, downloadBlob fallback
- downloadBlob centralizzato (era duplicato identico in 2 file)
- Export singolo esistente invariato