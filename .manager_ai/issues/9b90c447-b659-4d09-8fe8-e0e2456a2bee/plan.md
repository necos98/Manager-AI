## Implementation Plan

### Task 1: Update cors_origins in config.py to include port 4173 and env var override
**File:** `backend/app/config.py`
- Add `http://localhost:4173` and `http://127.0.0.1:4173` to the default `cors_origins` string
- The model_config already has `env_file = ".env"`, and Pydantic BaseSettings automatically reads env vars matching field names (case-insensitive). No code change needed for env var support — just document it

### Task 2: Add `enabled: Boolean(projectId)` guard to useIssues hook
**File:** `frontend/src/features/issues/hooks.ts`
- Add `enabled: Boolean(projectId)` to the useQuery config in `useIssues`
- This prevents the hook from fetching when projectId is empty/undefined, avoiding the double-slash URL

### Task 3: Audit and fix other hooks missing projectId guard
**Files:** `frontend/src/features/issues/hooks.ts`, `frontend/src/features/issues/api.ts`
- Check all query hooks in this module — `useIssue`, `useProjectTags`, `useFeedback`, etc.
- Add `enabled: Boolean(projectId)` where missing

### Verification
- Verify CORS config change by checking the file content
- Verify frontend hook changes by reading the modified files
- Test the backend syntax: `python -c "import ast; ast.parse(open('backend/app/config.py').read())"`
- Test the frontend syntax: `cd frontend && npx tsc --noEmit --pretty` (or just check valid JSX/TSX)