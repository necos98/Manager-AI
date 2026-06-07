9. pipeline_run_service.py:243-425 — _execute() di 182 righe

  Gestisce session, fetch pipeline, loop step, creazione terminale, WSL, event emission, esecuzione step, cleanup,
  finalizzazione.
  Fix: Estrarre _execute_single_step(), _create_terminal_for_step(), _handle_wsl_cd(), _finalize_run()