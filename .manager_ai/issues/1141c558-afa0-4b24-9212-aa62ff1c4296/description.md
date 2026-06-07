 13. terminals.py:482-486 e projects.py:476-486 — URL non quotato in comandi shell

  pty.write(f"claude mcp add ManagerAi --transport http \"{url}\"\r\n")
  shlex.quote() NON è usato per l'URL. Se host IP contiene metacaratteri shell → command injection.