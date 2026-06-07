 12. terminal_service.py:138 — Command injection WSL

  pty.spawn(f'"{shell_to_use}" -d {wsl_distro}', cwd=spawn_cwd)
  wsl_distro validato con regex ma interpolato direttamente in stringa shell. shell_to_use viene da MANAGER_AI_SHELL env
   var controllabile dall'utente.