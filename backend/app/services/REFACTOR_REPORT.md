# Refactoring Report: pipeline_run_service.py & issue_service.py

## 1. pipeline_run_service.py (818 righe)

### Responsabilita attuali (6 mescolate)
1. **Orchestrazione esecuzione pipeline**: start(), _execute(), _finalize_run()
2. **Step lifecycle**: _setup_step_environment(), _run_step(), reject_step(), _cleanup_step()
3. **Query pipeline runs**: get_run(), get_runs_for_issue(), get_active_runs_for_project()
4. **Messaggistica**: add_message(), get_messages()
5. **Sessioni DB**: _safe_flush_session(), _safe_commit_session()
6. **Modulo globale**: set_step_completed(), _step_completion_events

### Duplicazioni chiave
- Serializzazione step_run->dict identica in 3 metodi
- Pattern event_service.emit() ripetuto in 7+ punti
- Lazy import di PipelineService, Project, wsl_support, TerminalSession

### Refactoring proposto
1. PipelineRunOrchestrator - orchestrazione
2. PipelineStepExecutor - step execution
3. PipelineRunQueryService - read model
4. PipelineMessageService - messaggi
5. PipelineSerializationHelper - step_run->dict

## 2. issue_service.py (462 righe)

### Responsabilita attuali (4 mescolate)
1. **CRUD issue**: create(), get_by_id(), list_by_project(), update_fields(), delete()
2. **State machine**: create_spec(), edit_spec(), create_plan(), accept_issue(), complete_issue()
3. **Feedback**: add_feedback(), list_feedback()
4. **Tags**: get_project_tags()

### Duplicazioni chiave
- hook_registry.fire() + ActivityService.log() identico in 6 metodi
- issue_store.update_issue() + _resolve_path() ripetuto in 10+ punti
- Pattern validazione spec/plan identico in 4 metodi

### Refactoring proposto
1. IssueCrudService - CRUD base
2. IssueLifecycleService - state machine
3. IssueFeedbackService - feedback
4. IssueTagService - tags
5. IssueEventHelper - log+hooks centralizzato

## 3. Dipendenze critiche
- pipeline_run_service importa moduli PRIVATI (_sessions, _stop_reader)
- Lazy import circolare: PipelineService, terminal_session
- issue_service usa DB solo per ProjectService + ActivityService + hooks

## 4. Impatto
- 1280 righe -> circa 800 righe totali
- 7-8 nuovi file, ciascuno <200 righe
- Dipendenze circolari risolte
