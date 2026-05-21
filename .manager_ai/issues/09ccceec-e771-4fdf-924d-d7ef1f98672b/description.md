Pipeline full-lifecycle: Orchestrator gestisce issue dall'inizio alla fine (NEW → FINISHED). 

Stato attuale: la pipeline parte solo dopo accept_issue (PLANNED → ACCEPTED), coprendo solo sviluppo/review/QA. La fase di planning (spec + plan) è fuori dalla pipeline. Inoltre manca il pulsante "Start Pipeline" in UI — oggi solo "Run Issue" che spawna Claude Code singolo senza pipeline.

Obiettivi:
1. Nuovo agente SpecWriter che si occupa di analizzare requisiti e scrivere spec + plan
2. Pipeline default 5-step: SpecWriter → Architect → Developer → Reviewer → QA
3. Orchestrator gestisce TUTTO il ciclo vita: dalla issue NEW fino a FINISHED
4. Pulsante "Start Pipeline" nella issue detail (simile a "Run Issue") per avviare manualmente la pipeline
5. La pipeline deve poter partire da qualsiasi stato (non solo ACCEPTED)