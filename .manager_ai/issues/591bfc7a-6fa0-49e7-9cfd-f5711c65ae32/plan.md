# Implementation Plan

## Obiettivo
Sostituire le due creazioni dirette di `IssueQueueService()` in `routers/queue.py` con l'uso del singleton `issue_queue_service_ref` già importato.

## Strategia

Il singleton `issue_queue_service_ref` è già importato a linea 21 del file. I due endpoint che lo ignorano devono essere allineati al pattern già usato da `POST /api/queue/auto-process` (righe 248-249).

## Task

### Task 1: Fix `remove_from_queue()` (linea 329)
- Sostituire `registry = IssueQueueService()` con `registry = issue_queue_service_ref`
- Aggiungere guard `if registry is None: raise HTTPException(503, "Queue service not initialized")`

### Task 2: Fix `get_queue_position()` (linea 374)
- Sostituire `registry = IssueQueueService()` con `registry = issue_queue_service_ref`
- Aggiungere guard `if registry is None: ...`

### Task 3: Verifica
- Sintassi: `python -c "import ast; ast.parse(open('backend/app/routers/queue.py').read())"`
- Test endpoint con curl sul backend in esecuzione
