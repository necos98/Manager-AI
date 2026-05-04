## Implementation Recap

Integrated Playwright E2E testing support into Manager AI with credential management.

### What was built

**Backend (8 commits):**
- `ProjectCredential` SQLAlchemy model with unique constraint on (project_id, role)
- `Project.url` column for storing the web app base URL
- `CredentialService` with Fernet encryption (key from `MANAGER_AI_SECRET_KEY` env var, auto-generated if absent)
- REST API: `GET/POST/DELETE /api/projects/{id}/credentials`, `GET /api/projects/{id}/credentials/{role}`
- 5 MCP tools: `get_project_url`, `list_credentials`, `get_credential`, `set_credential`, `delete_credential`
- Alembic migration for `project_credentials` table + `projects.url` column

**Frontend (3 commits):**
- `ProjectCredential` and `CredentialUpsert` TypeScript types
- `url` field added to Project/ProjectCreate/ProjectUpdate types
- API layer: `fetchCredentials`, `fetchCredential`, `upsertCredential`, `deleteCredential`
- React Query hooks: `useCredentials`, `useCredential`, `useUpsertCredential`, `useDeleteCredential`
- Project settings dialog: URL field + Test Credentials section (list/add/delete)

### Verification
- Credential CRUD flow tested end-to-end against in-memory SQLite
- Encryption/decryption verified: credentials stored encrypted, returned decrypted
- Migration applies cleanly
- Backend tests: 283 passed, 1 skipped (1 pre-existing failure unrelated to changes)

### Deferred
- Playwright MCP server lifecycle management (spawn/health check/kill) — tracked separately
- The `@playwright/mcp` package itself is NOT installed; this issue provides the credential infrastructure that Playwright will consume via MCP tools