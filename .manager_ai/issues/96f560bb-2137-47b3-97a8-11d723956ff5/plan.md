## Files Modified

| File | Change |
|---|---|
| `backend/app/services/credential_service.py:17-25` | Replace `Fernet.generate_key()` fallback with `ValueError` |
| `backend/app/main.py:331-350` | Add startup key persistence in lifespan (read/generate `data/secret.key`) |
| `.env.example:17` | Add `MANAGER_AI_SECRET_KEY` documentation |

## Tasks

### Task 1: Hard error guard in `_get_fernet()`
- Replace `os.environ.get("MANAGER_AI_SECRET_KEY") or Fernet.generate_key()` with explicit env var read + `ValueError` if unset
- Error message directs user to key persistence mechanism

### Task 2: Startup key persistence in `main.py` lifespan
- Before any handler runs: if env var not set, check `data/secret.key`
- If file exists: read key into env var
- If missing: generate key, write atomically (temp+rename via `os.replace`)

### Task 3: Document in `.env.example`
- Add `MANAGER_AI_SECRET_KEY` entry with comment explaining auto-generation to `data/secret.key`

## Dependencies
- None — all 3 tasks are independent
- Task 1 depends on Task 2 logically (guard is safe because lifespan ensures key exists), but code works independently
