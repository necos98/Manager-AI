Quando cerco di avviare una pipeline mi esce un errore molto strano, che non fa avviare il terminale, ma se cancello l'esecuzione della pipeline e la rieseguo, funziona. 

Ecco l'errore in console:

[06/04/26 12:39:57] ERROR    Task exception was never retrieved                                                                                                                               base_events.py:1875
                             future: <Task finished name='Task-514' coro=<PipelineRunService._execute() done, defined at
                             C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\pipeline_run_service.py:234> exception=NotFoundError('Pipeline run not found:
                             a45c4213-5853-47ed-91dd-4504d14eefd4')>
                             ╭───────────────────────────────────────────────────────────── Traceback (most recent call last) ──────────────────────────────────────────────────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\pipeline_run_service.py:242 in _execute                                              │
                             │                                                                                                                                                              │
                             │   239 │   │   │   session = self.session_factory()                                                                                                           │
                             │   240 │   │                                                                                                                                                  │
                             │   241 │   │   try:                                                                                                                                           │
                             │ ❱ 242 │   │   │   run = await self._get_run_with_session(run_id, session)                                                                                    │
                             │   243 │   │   │   pipeline = await session.execute(                                                                                                          │
                             │   244 │   │   │   │   select(Pipeline)                                                                                                                       │
                             │   245 │   │   │   │   .where(Pipeline.id == run.pipeline_id)                                                                                                 │
                             │                                                                                                                                                              │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\pipeline_run_service.py:497 in _get_run_with_session                                 │
                             │                                                                                                                                                              │
                             │   494 │   │   )                                                                                                                                              │
                             │   495 │   │   run = result.unique().scalar_one_or_none()                                                                                                     │
                             │   496 │   │   if run is None:                                                                                                                                │
                             │ ❱ 497 │   │   │   raise NotFoundError(f"Pipeline run not found: {run_id}")                                                                                   │
                             │   498 │   │   return run                                                                                                                                     │
                             │   499 │                                                                                                                                                      │
                             │   500 │   async def get_run(self, run_id: str) -> dict:                                                                                                      │
                             ╰───────────────
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                             NotFoundError: Pipeline run not found: a45c4213-5853-47ed-91dd-4504d14eefd4