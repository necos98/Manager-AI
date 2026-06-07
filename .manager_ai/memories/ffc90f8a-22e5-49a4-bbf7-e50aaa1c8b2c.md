---
id: ffc90f8a-22e5-49a4-bbf7-e50aaa1c8b2c
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: URL quoting helper in wsl_support.py
parent_id: null
created_at: '2026-06-05T12:18:11.216425'
updated_at: '2026-06-05T12:18:11.216425'
links: []
---
Decision: quote_url_for_shell(url, is_wsl) lives in wsl_support.py (not a new module). Rationale: both consumers (terminals.py, projects.py) already import from wsl_support. Uses shlex.quote() for bash/WSL, double-quote wrapping for cmd.exe — follows the same dialect pattern as _inject_env_vars() in terminals.py. This is complementary to the 3-layer shell_to_use defense in memory 0c7ad026.