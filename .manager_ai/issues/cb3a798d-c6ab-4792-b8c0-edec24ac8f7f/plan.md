## Implementation Plan: Fix CORS misconfiguration (wildcard origin + credentials)

### Problem Summary

`backend/app/main.py:511` sets `allow_origins=["*"]` while `allow_credentials=True` is on line 512. Per CORS spec, browsers reject credentialed requests when the origin is `*`. Fix: configure specific origins via env var.

### Files to Change

| File | Change |
|------|--------|
| `backend/app/config.py` | Add `cors_origins: str` field to `Settings` class |
| `backend/app/main.py` | Replace `["*"]` with `settings.cors_origins.split(",")` |
| `.env.example` | Add `# --- CORS ---` section with `CORS_ORIGINS` variable |

### Step-by-Step

#### Step 1: Add `cors_origins` to Settings (`backend/app/config.py`)

Add this field after `terminal_max_buffer_bytes`:

```python
cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
```

- Default covers the Vite dev server on both `localhost` and `127.0.0.1` (common Windows/macOS divergence)
- No validator needed — per spec, invalid origins just don't match (harmless)
- Follows existing `pydantic_settings.BaseSettings` pattern, reads from `CORS_ORIGINS` env var automatically

#### Step 2: Update middleware origin (`backend/app/main.py`)

Line 511 change:

```python
# Before:
allow_origins=["*"],

# After:
allow_origins=settings.cors_origins.split(","),
```

- `settings` already imported at line 13 — no import change
- `.split(",")` handles the comma-separated format
- `CORS_ORIGINS=*` → `"*".split(",")` → `["*"]` — restores wildcard for non-credentialed use cases
- `CORS_ORIGINS=` (empty) → `"".split(",")` → `[""]` — harmless, no origin will match
- No other CORS middleware parameters changed — `allow_credentials`, `allow_methods`, `allow_headers` stay as-is

#### Step 3: Document in `.env.example`

Add after the last section (`# --- Storage paths ---`):

```
# --- CORS ---
# CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

- Commented out by default (shows the default value)
- Follows existing `# VAR=value` comment convention in the file

### Edge Cases & Behaviors

| Env Var Value | Resulting `allow_origins` | Valid? |
|---|---|---|
| Not set (default) | `["http://localhost:5173", "http://127.0.0.1:5173"]` | Yes |
| `CORS_ORIGINS=*` | `["*"]` | Yes (but no credentials) |
| `CORS_ORIGINS=https://app.com` | `["https://app.com"]` | Yes |
| `CORS_ORIGINS=a.com,b.com` | `["a.com", "b.com"]` | Yes |
| `CORS_ORIGINS=` (empty) | `[""]` | Harmless (no matches) |

### Dev / Test Verification

1. Start backend without `.env` — verify `allow_origins` = `["http://localhost:5173", "http://127.0.0.1:5173"]`
2. Set `CORS_ORIGINS=*` in `.env` — verify `allow_origins` = `["*"]`
3. Set `CORS_ORIGINS=http://example.com` — verify `allow_origins` = `["http://example.com"]`
4. Verify backend starts without errors in all cases

### Why This Approach

- **Minimal**: ~3 lines added, ~1 line changed — smallest possible fix
- **Consistent**: follows existing `pydantic_settings` pattern (like `backend_port`, `database_url`)
- **Non-breaking**: old behavior (wildcard) restorable via `CORS_ORIGINS=*`
- **Zero deps**: no new libraries, no refactoring
