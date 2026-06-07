CORS misconfiguration fix implemented and verified.

**What was done:**
1. Added `cors_origins: str` to `Settings` in `config.py` — defaults to Vite dev server ports (localhost:5173, 127.0.0.1:5173)
2. Replaced `allow_origins=["*"]` with `settings.cors_origins.split(",")` in `main.py:511`
3. Added `# --- CORS ---` section with `CORS_ORIGINS` to `.env.example`

**Verification:**
- Code changes verified correct against spec and plan
- Full test suite: 590 passed, 33 failed, 15 errors — all failures pre-existing from other uncommitted changes (30+ files modified across frontend/backend), none related to CORS fix

**Known issue (out of scope — developer-added secret key code):**
- `main.py:331-351` adds MANAGER_AI_SECRET_KEY auto-generation using relative path `os.path.join("data", "secret.key")` — crashes on fresh clone if `data/` dir missing. Flagged by CodeReview as BLOCKER. Not addressed in this issue's scope.