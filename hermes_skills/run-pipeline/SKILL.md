---
name: run-pipeline
description: "Esegui uno step di pipeline di Manager AI — scopri la tua identità, leggi il contesto, esegui, segnala completamento"
version: 1.0.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Run Pipeline

Sei stato spawnato per eseguire uno **step di pipeline** di Manager AI. L'issue ID è nel messaggio dell'utente (la `-q` query).

## Prerequisiti

Manager AI deve essere in esecuzione (`python start.py` dal repo Manager-AI).  
Il worker MCP deve essere configurato in Hermes:

```bash
hermes mcp add manager-ai-worker --url http://localhost:8000/mcp/
```

## 1. Scopri la tua identità

Sei **l'agente attivo** in questa pipeline. `worker_get_active_agent` ti dice chi sei.

Chiama `worker_get_active_agent` con l'issue ID. La risposta ti identifica:

- **agent_name** — il tuo nome (es. "SpecWriter", "Developer")
- **agent_intent** — la **tua istruzione primaria**. È il campo più importante. Leggilo con attenzione e seguilo.
- **run_id**, **step_run_id**, **step_index**, **terminal_id** — il tuo contesto di esecuzione

`worker_get_active_agent` è l'**UNICA** fonte della tua identità. Non ci sono env var, nessun canale secondario. Chiamalo una volta, interiorizza il risultato e agisci.

Se `worker_get_active_agent` ritorna null, nessuna pipeline è in esecuzione per questa issue. Segnalalo e fermati.

## 2. Leggi il contesto della pipeline

Chiama `worker_get_active_pipeline_run` con l'issue ID per vedere:
- Quali step sono completati, quale sta girando, quali sono pending
- Chi sono gli altri agenti e cosa fanno
- Dove ti collochi nel workflow complessivo

## 3. Leggi la issue

Chiama `worker_get_issue_details` con l'issue ID. Il `project_id` è in `manager.json` nella root del progetto.

## 4. Leggi i messaggi della pipeline (handoff dagli agenti precedenti)

Chiama `worker_get_pipeline_messages` con il tuo `run_id`. Ritorna tutti i messaggi ordinati per creazione, ognuno con `sender_agent_name`, `content` e `created_at`.

- Leggi i messaggi degli agenti che hanno girato **prima di te** — contengono risultati di analisi, razionali per le decisioni, constraint scoperti e suggerimenti per l'implementazione.
- I messaggi sono il tuo meccanismo di handoff primario. Trattali come lettura obbligatoria prima di iniziare il lavoro.
- Se sei il primo agente della pipeline, non ci saranno messaggi — è normale, parti da zero.

## 5. Esegui la tua intest

Il campo `intent` del tuo agente ti dice cosa fare. Usalo come istruzione primaria. Mappa la tua intent ai tool MCP appropriati:

- **Spec / Design intent** (analizzare requisiti, scrivere specifiche, brainstorming): usa `worker_set_issue_name` se la issue manca di un buon nome, analizza i requisiti, produce una specifica e salvala via `create_issue_spec`.

- **Planning intent** (scomporre il lavoro, creare piani di implementazione): leggi la spec via `worker_get_issue_details`, poi crea il piano di implementazione via `create_issue_plan` e task atomici via `create_plan_tasks`.

- **Implementation intent** (scrivere codice, fare modifiche): leggi i plan task via `get_plan_tasks`, lavorali sequenzialmente — imposta ognuno a "In Progress" quando inizi, "Completed" quando finisci. Segui i pattern esistenti del codebase. Prendi decisioni autonome — non chiedere conferme. Se bloccato, usa `ask_user_question`.

- **Exploration / Analysis intent** (capire il codebase, tracciare path): esplora il codebase, traccia i path di codice rilevanti, identifica i file che necessitano modifiche, documenta pattern e dipendenze. **Non modificare file** — è solo analisi.

- **Review / QA intent** (verificare correttezza, testare): rivedi le modifiche per bug, errori logici, problemi di sicurezza e aderenza alle convenzioni del progetto. Esegui test, verifica comportamento, riporta risultati.

- **Se la tua intent non mappa chiaramente a nessuno dei precedenti**: rileggi la intent e usa il tuo miglior giudizio. Usa i tool MCP disponibili come appropriato.

## 6. Segnala completamento

Quando il tuo step è completo, chiama `finished_pipeline_step` con:

- `issue_id`: l'ID della issue
- `summary`: un handoff summary chiaro che copra **cosa hai fatto**, **decisioni chiave e perché**, **file cambiati / artefatti creati**, **constraint o gotcha scoperti** e **indicazioni specifiche per il prossimo agente** (es. "i plan task sono pronti, inizia da task 1", "il modulo auth richiede gestione speciale — vedi note sopra").

- `rejected` (opzionale, default `false`): imposta a `true` se il lavoro dello step precedente **NON** è accettabile e necessita di rielaborazione.
- `rejection_reason` (richiesto se `rejected: true`): spiega esattamente cosa non va e cosa deve essere fixato — sii specifico (file, logica, pezzi mancanti).
- `target_step_index` (opzionale, usato con `rejected: true`): indice dello step a cui rimandare il lavoro. Default: lo step immediatamente precedente.

### Quando rifiutare

Usa `rejected: true` quando l'output di un agente precedente ha problemi **bloccanti**: logica incorretta, falle di sicurezza, spec non corrisponde ai requisiti, piano manca pezzi chiave, codice non compila o fallisce i test, qualità inaccettabile. Per problemi minori, includili nel summary e lascia che sia il prossimo agente a gestirli.

**Review / QA agenti** dovrebbero rifiutare liberalmente — il quality gate è il tuo lavoro. Fornisci un `rejection_reason` chiaro così l'agente target sa esattamente cosa fixare.

### Come funziona il routing

- `rejected: false` (default): la pipeline avanza allo step successivo normalmente.
- `rejected: true` senza `target_step_index`: il lavoro torna allo step immediatamente precedente. L'agente di quello step viene reinvocato per fixare i problemi.
- `rejected: true` con `target_step_index`: il lavoro torna allo step specificato (es. rimanda un'implementazione fallata allo step Developer invece che a TaskWriter). La pipeline si resetta — tutti gli step dopo il target vengono marcati come pending e rieseguiti dopo il fix.

### Memoria

Prima di uscire, chiama `memory_create` (via MCP Manager AI) per qualsiasi fatto durevole e non ovvio appreso — decisioni architetturali, constraint, gotcha, preferenze utente.

## 7. Complete

Dopo aver chiamato `finished_pipeline_step`, esci semplicemente. L'orchestratore chiuderà il tuo terminale e avanzerà al prossimo agente automaticamente.
