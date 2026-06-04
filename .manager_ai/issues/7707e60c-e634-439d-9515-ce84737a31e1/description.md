errore durante l'esecuzione di una Pipeline:

INFO:     127.0.0.1:51049 - "GET /api/projects/1baae1c7-22f1-4091-abec-b49da70cf46c/issues/df953160-e8b3-4410-84e5-e0c4be5a9efd HTTP/1.1" 200 OK
[06/04/26 21:30:16] ERROR    Task exception was never retrieved                                      base_events.py:1875
                             future: <Task finished name='Task-97'
                             coro=<PipelineRunService._execute() done, defined at
                             C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services
                             \pipeline_run_service.py:240> exception=MultipleResultsFound('Multiple
                             rows were found when one or none was required')>
                             ╭───────────────── Traceback (most recent call last) ─────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\serv │
                             │ ices\pipeline_run_service.py:273 in _execute                        │
                             │                                                                     │
                             │   270 │   │   │   │   │   │   PipelineStepRun.pipeline_step_id == s │
                             │   271 │   │   │   │   │   ).order_by(PipelineStepRun.started_at.des │
                             │   272 │   │   │   │   )                                             │
                             │ ❱ 273 │   │   │   │   step_run = step_run_result.scalar_one_or_none │
                             │   274 │   │   │   │   if step_run is None:                          │
                             │   275 │   │   │   │   │   continue                                  │
                             │   276                                                               │
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
INFO:     127.0.0.1:58301 - "GET /api/projects/1baae1c7-22f1-4091-abec-b49da70cf46c/issues/df953160-e8b3-4410-84e5-e0c4be5a9efd HTTP/1.1" 200 OK
INFO:     127.0.0.1:63601 - "GET /api/terminals?issue_id=df953160-e8b3-4410-84e5-e0c4be5a9efd HTTP/1.1" 200 OK
INFO:     connection closed
[06/04/26 21:30:17] INFO     Created new transport with session ID:                       streamable_http_manager.py:229
                             1fc797739d7b4794a47a193173cf3786
INFO:     ('127.0.0.1', 63601) - "WebSocket /api/terminals/0c1904b5-218b-43e3-90d0-f4c47d1a7795/ws" 403
INFO:     connection rejected (403 Forbidden)
INFO:     127.0.0.1:54976 - "GET /api/terminals/count HTTP/1.1" 200 OK
INFO:     connection closed