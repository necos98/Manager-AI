## Problem

`CredentialService._get_fernet()` in `credential_service.py` silently generates a random Fernet key when `MANAGER_AI_SECRET_KEY` is not set:

```python
key = os.environ.get("MANAGER_AI_SECRET_KEY") or Fernet.generate_key()
```

The generated key lives only in process memory. On server restart, all previously encrypted credentials become permanently unreadable — silent corruption with no warning to the user.

## Solution (3 parts)

### 1. Hard error in `_get_fernet()` — no silent fallback

Replace `Fernet.generate_key()` fallback with `ValueError`. If `MANAGER_AI_SECRET_KEY` is not set, any credential operation fails immediately with a clear error message directing the user to the startup persistence mechanism.

**File:** `backend/app/services/credential_service.py:17-25`

### 2. Startup key persistence in `main.py` lifespan

Before any request handler runs, ensure `MANAGER_AI_SECRET_KEY` is available:

- **Env var takes precedence** — if already set, use as-is
- **Check `data/secret.key`** — if file exists, read key into env var
- **Generate + persist** — if neither exists, generate new key, write atomically (temp file + `os.replace`)

**File:** `backend/app/main.py:331-350`

### 3. Documentation in `.env.example`

Add `MANAGER_AI_SECRET_KEY` with comment explaining it's auto-generated to `data/secret.key` on first start.

**File:** `.env.example:17`

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Env var vs file priority | Env var wins | Allows override in production deployments (Docker, CI) |
| Write strategy | Atomic temp+rename | Prevents partial/corrupt key file on crash during write |
| Error type | `ValueError` | Callers already handle this as HTTP 500; no new exception type needed |
| Key file location | `data/secret.key` | Inside `data/` dir which is gitignored; consistent with other runtime data |

## Verification

- Restart server without `MANAGER_AI_SECRET_KEY` — key auto-generated to `data/secret.key`, credentials readable
- Restart server with `MANAGER_AI_SECRET_KEY` set — env var used, `data/secret.key` ignored
- Delete `MANAGER_AI_SECRET_KEY` from env and `data/secret.key` — `_get_fernet()` raises `ValueError`
