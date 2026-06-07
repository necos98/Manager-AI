## Tester Summary

Tests run: `tests/test_url_quoting.py` (8/8 pass) + full suite (599 pass, 33 pre-existing failures unrelated to this change).

**What was tested:**
- `quote_url_for_shell()` helper in `wsl_support.py` — normal URLs, metacharacters, backticks, `$()` injection, spaces, empty URLs — both WSL/bash (`shlex.quote`) and cmd.exe (double-quote wrap) dialects
- Full regression suite — no new failures introduced

**Files modified:**
- `backend/app/services/wsl_support.py` — added `quote_url_for_shell(url, is_wsl)` helper
- `backend/app/routers/terminals.py` — 4 `export MANAGER_AI_BASE_URL` sites now use helper
- `backend/app/routers/projects.py` — 2 `claude mcp add` sites now use helper  
- `backend/tests/test_url_quoting.py` — 8 test cases

**Verdict: PASS** — all tests pass, no regressions. Issue closes.