Credo sia successo questo bug quando un agente ha rejectato uno step e quindi il task è ritornato all'agente precedente, nella pipeline è completamente scomparso il terminale (vedi errore sotto) e la pipeline dice che è in esecuzione quando non è assolutamente vero:

INFO:     127.0.0.1:50566 - "GET /api/projects/1baae1c7-22f1-4091-abec-b49da70cf46c/issues?status=Finished&limit=10 HTTP/1.1" 200 OK
[06/05/26 12:56:43] ERROR    Task exception was never retrieved                                      base_events.py:1875
                             future: <Task finished name='Task-8787'
                             coro=<PipelineRunService._execute() done, defined at
                             C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services
                             \pipeline_run_service.py:242> exception=MultipleResultsFound('Multiple
                             rows were found when one or none was required')>
                             ╭───────────────── Traceback (most recent call last) ─────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\serv │
                             │ ices\pipeline_run_service.py:275 in _execute                        │
                             │                                                                     │
                             │   272 │   │   │   │   │   │   PipelineStepRun.pipeline_step_id == s │
                             │   273 │   │   │   │   │   ).order_by(PipelineStepRun.started_at.des │
                             │   274 │   │   │   │   )                                             │
                             │ ❱ 275 │   │   │   │   step_run = step_run_result.scalar_one_or_none │
                             │   276 │   │   │   │   if step_run is None:                          │
                             │   277 │   │   │   │   │   continue                                  │
                             │   278                                                               │
                             │                                                                     │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-pa │
                             │ ckages\sqlalchemy\engine\result.py:1504 in scalar_one_or_none       │
                             │                                                                     │
                             │   1501 │   │   │   :meth:`_engine.Result.scalars`                   │
                             │   1502 │   │                                                        │
                             │   1503 │   │   """                                                  │
                             │ ❱ 1504 │   │   return self._only_one_row(                           │
                             │   1505 │   │   │   raise_for_second_row=True, raise_for_none=False, │
                             │   1506 │   │   )                                                    │
                             │   1507                                                              │
                             │                                                                     │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-pa │
                             │ ckages\sqlalchemy\engine\result.py:825 in _only_one_row             │
                             │                                                                     │
                             │    822 │   │   │                                                    │
                             │    823 │   │   │   if next_row is not _NO_ROW:                      │
                             │    824 │   │   │   │   self._soft_close(hard=True)                  │
                             │ ❱  825 │   │   │   │   raise exc.MultipleResultsFound(              │
                             │    826 │   │   │   │   │   "Multiple rows were found when exactly o │
                             │    827 │   │   │   │   │   if raise_for_none                        │
                             │    828 │   │   │   │   │   else "Multiple rows were found when one  │
                             ╰─────────────────────────────────────────────────────────────────────╯
                             MultipleResultsFound: Multiple rows were found when one or none was
                             required
                    INFO     Created new transport with session ID:                       streamable_http_manager.py:229
                             ea021ee4fb84486ebbe7797878de11aa