 7. main.py:325-473 — Lifespan di 148 righe monolitico

  14 operazioni sequenziali. Ogni step wrappato in try/except che silenzia errori. Se un progetto fallisce, gli altri
  non vengono caricati.
  Fix: Decomporre in _startup_migrate(), _startup_load_projects(), _startup_seed_defaults(),
  _startup_cleanup_orphaned_runs()