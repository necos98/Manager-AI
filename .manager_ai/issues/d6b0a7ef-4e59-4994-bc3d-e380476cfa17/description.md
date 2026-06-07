20. issue_service.py:37-38 — _issue_completion_locks dict senza cleanup

  Module-level dict cresce per sempre. Ogni issue completata lascia un lock nel dict.