# Specifica: Rilassare il guard `pending_count == 1` in `_maybe_auto_start_first()`

## Problema

`_maybe_auto_start_first()` è chiamata quando una nuova issue viene accodata (da `_on_issue_queued`). Il suo scopo è avviare automaticamente la prima issue in coda se non c'è già una issue in esecuzione.

Attualmente ha questo guard:

```python
if pending_count != 1:
    return
```

Cioè parte **solo** se c'è esattamente 1 entry PENDING nella coda. Questo è troppo conservativo per i seguenti scenari:

1. **Auto-processing abilitato dopo che la coda ha già >1 pending** — Se l'auto-processing viene attivato dopo che più issue sono già state aggiunte alla coda, `_maybe_auto_start_first` non fa partire nulla perché pending_count > 1. `set_enabled(true)` chiama `startup_resume()` come workaround, ma se `startup_resume` fallisce (eccezione silenziosa, problema DB) non c'è retry e la coda rimane bloccata.

2. **startup_resume fallisce** — `startup_resume()` scandisce tutti i progetti e chiama `_dequeue_and_run()` per ciascuno. Se fallisce per un progetto, la coda per quel progetto rimane stallata finché non arriva un Finished event (che non arriverà mai perché nessuna issue è partita).

## Soluzione

Rilassare il guard da `pending_count != 1` a `pending_count < 1` (cioè >= 1):

```python
if pending_count < 1:
    return
```

Questo significa: "auto-start **ogni volta che** c'è almeno una pending entry e nessuna issue è in esecuzione per questo progetto."

**Sicurezza:** Il metodo ha già un secondo guard che controlla se c'è un issue in stato REASONING per il progetto (`running = await issue_service.list_by_project(project_id, status=IssueStatus.REASONING)`). Inoltre `_dequeue_and_run` ha un lock per-progetto che serializza le esecuzioni. Non c'è rischio di doppio start.

## Analisi impatto

- **`_on_issue_finished`** chiama già `_dequeue_and_run()` direttamente — non è toccata.
- **`_on_issue_queued`** chiama `_maybe_auto_start_first()` dopo aver registrato la nuova entry. Con pending_count >= 1, la coda partirà in questi casi:
  - Prima issue aggiunta (pending_count=1) — stesso comportamento di prima
  - Issue aggiunta mentre ce n'è già una in attesa (pending_count=2+) e nessuna in esecuzione — **nuovo comportamento**, corretto
  - Issue aggiunta mentre un'altra è in esecuzione — il guard `running` impedisce il doppio start — sicuro
- **Test `test_skips_when_multiple_pending`** — cambia semantica: ora DEVE auto-startare se c'è >1 pending e nulla è in esecuzione. Il test va aggiornato.
- **Test `test_skips_when_issue_running`** — rimane invariato.
- **Test `test_skips_when_no_pending_entries`** — rimane invariato.
- **Test `test_auto_starts_when_only_pending`** — rimane invariato.

## File da modificare

1. `backend/app/services/issue_queue_service.py` — cambiare `pending_count != 1` in `pending_count < 1` (riga 538)
2. `backend/tests/test_issue_queue_service.py` — aggiornare `test_skips_when_multiple_pending` per riflettere la nuova semantica