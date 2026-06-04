## Problem

When a user clicks on a project in the frontend, the issues page loads slowly (multiple seconds of delay). The root cause is an N+1 query pattern in the issue relations loading: the frontend fires one API call per issue (`GET /api/issues/{issue_id}/relations`) to determine blocked status on the kanban board. With 20+ issues on a board, this means 20+ parallel API calls. Each backend call independently scans all issues across all projects, making the total cost O(N × P × I).

## Scope

Add a batch endpoint and update the frontend to use it — replacing N individual relation-fetch calls with a single batch call.

### Backend

- **New endpoint**: `POST /api/issues/relations/batch` accepting `{"issue_ids": ["id1", "id2", ...]}` and returning `{ blocked_ids: string[] }` — the subset of requested issue IDs that are blocked by other issues.
- **Service method**: `get_blocked_issue_ids(issue_ids: list[str])` in `issue_relation_service.py` that scans the issue store once and returns which of the given issue IDs are blocked. One scan total, not one per issue.
- **Router**: New route in `issue_relations.py`.

### Frontend

- **New API function**: `fetchBlockedIssueIds(issueIds)` in `api-relations.ts`.
- **Updated hook**: `useBlockedIssueIds` in `hooks-relations.ts` — replace `useQueries` (N calls) with a single `useQuery` calling the batch endpoint.

### Data shape consumed by kanban

`useBlockedIssueIds(issues)` returns `Set<string>` — the set of issue IDs that are blocked. The kanban board receives this as `blockedIssueIds` and only calls `.has(issue.id)` to determine if a card shows the blocked indicator. The batch endpoint returns `{ blocked_ids: string[] }` which the hook converts to `Set<string>`, keeping the consumer interface identical.

## Constraints

- Backend uses in-memory MemoryStore — no SQL queries to optimize, the fix is purely about eliminating redundant iteration.
- The existing single-issue endpoint (`GET /api/issues/{issue_id}/relations`) must remain for backward compatibility (other callers may use it).
- Response time for a board with 50 issues must be ~same as response time for a single issue (one scan, not 50).

## Acceptance Criteria

1. `POST /api/issues/relations/batch` returns correct blocked IDs for N issues in a single request.
2. Frontend kanban board loads issue blocked status with 1 API call instead of N.
3. No regression in single-issue relation endpoint.
4. All existing tests pass.
5. Board with 50+ issues loads blocked status in < 500ms (vs. seconds currently).

## Non-goals

- No changes to the kanban board component itself.
- No pagination for the batch endpoint (expected max 100 issue IDs per request).
- No database-level optimization (the bottleneck is N passes not scan speed).
- No changes to other N+1 patterns outside issue relations.