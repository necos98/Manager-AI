Passare output strutturato tra step della pipeline in modo che ogni agente abbia il contesto di ciò che è stato fatto prima.

## Problema
Ogni step lancia `claude -p` fresco, senza contesto dei passaggi precedenti. L'architect non vede la spec scritta dallo SpecWriter se non tramite i campi `issue.specification` e `issue.plan` nel prompt. Il Developer non sa cosa ha deciso l'Architect. Il Reviewer non ha il summary dell'implementazione.

## Cosa fare
1. Arricchire `_build_prompt()` per includere:
   - Output degli step precedenti (dal campo `summary` di `AgentStepRun`)
   - Messaggi della agent chat (`get_agent_messages`) rilevanti per lo step corrente
2. Ogni agente deve scrivere un summary strutturato (non solo "completed successfully") — già supportato dal parametro `summary` di `complete_agent_step`
3. Aggiungere al prompt dello step N un riepilogo di tutti gli step 0..N-1 con:
   - Nome agente, ruolo, summary, decisioni chiave

## File interessati
- `backend/app/services/orchestrator_service.py` — `_build_prompt()` (righe 475-501)
- `backend/app/models/pipeline.py` — `AgentStepRun` ha già `summary`, verificare sia sufficiente

## Esempio prompt arricchito
```
## Previous Steps

### Step 1: SpecWriter (completed)
Summary: Defined REST API with 3 endpoints...
Key decisions: Use Pydantic v2 for validation, async SQLAlchemy...

### Step 2: Architect (completed)  
Summary: Chose layered architecture with service/repository pattern...
Key decisions: Separate read/write models, use dependency injection...
```