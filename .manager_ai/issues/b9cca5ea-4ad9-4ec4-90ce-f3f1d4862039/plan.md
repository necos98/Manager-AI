## Implementation Plan: "Create issue from here"

### Overview

Add a "Create issue from here" button on the issue detail page action bar. Clicking opens NewIssueDialog pre-configured to create a new issue auto-linked as "related" to the source issue. The button is visible for ALL issue statuses (including Finished/Canceled, where IssueActions currently returns null).

### Architecture

**Backend flow**: Router receives IssueCreate with optional `source_issue_id`. After creating the issue via IssueService, if source_issue_id is present, call IssueRelationService.add_relation(new_id, source_id, "related"). Relation normalization (sorted IDs) happens inside add_relation — no extra logic needed.

**Frontend flow**: IssueDetail owns the dialog state. It renders a NewIssueDialog with optional sourceIssueId. IssueActions gets an `onCreateFromHere` callback prop. When clicked, IssueDetail opens the dialog. On submit, NewIssueDialog passes source_issue_id in the POST body. The backend creates the issue and the relation atomically (file-based, within the same request handler before db.commit).

### File Changes

---

#### Step 1: Backend — Add source_issue_id to IssueCreate schema

**File**: `backend/app/schemas/issue.py`
- Add `source_issue_id: str | None = None` field to `IssueCreate` class

---

#### Step 2: Backend — Handle source_issue_id in create endpoint

**File**: `backend/app/routers/issues.py`
- In `create_issue` handler, after `service.create()` succeeds and if `data.source_issue_id` is present:
  ```python
  if data.source_issue_id:
      from app.services.issue_relation_service import IssueRelationService
      from app.models.issue_relation import RelationType
      rel_service = IssueRelationService(db)
      await rel_service.add_relation(record.id, data.source_issue_id, RelationType.RELATED)
  ```
- Do this BEFORE `await db.commit()` so both the issue creation and relation creation are persisted in the same request cycle
- No changes needed to `issue_service.py` — relation creation is a separate concern handled at the router level (consistent with existing pattern, e.g., complete_issue endpoint fires hooks after service call)

---

#### Step 3: Frontend — Add source_issue_id to IssueCreate type

**File**: `frontend/src/shared/types/index.ts`
- Add `source_issue_id?: string;` to the `IssueCreate` interface

---

#### Step 4: Frontend — Add optional sourceIssueId prop to NewIssueDialog

**File**: `frontend/src/features/issues/components/new-issue-dialog.tsx`
- Add `sourceIssueId?: string` to the `Props` type
- In `handleSubmit`, include `source_issue_id: sourceIssueId` in the mutation data:
  ```ts
  createIssue.mutate(
    { description, priority, category, tags, ...(sourceIssueId ? { source_issue_id: sourceIssueId } : {}) },
    ...
  )
  ```

---

#### Step 5: Frontend — Add "Create issue from here" button to IssueActions

**File**: `frontend/src/features/issues/components/issue-actions.tsx`
- Add `onCreateFromHere?: () => void` to `IssueActionsProps`
- Add a "Create issue from here" button before the terminal-state guard
- Modify the terminal state guard: instead of `if (isTerminalState) return null;`, render only the "Create from here" button (and the confirm dialog if open) for terminal states. All other action buttons remain hidden.
- New button uses a `FilePlus` icon (already imported in new-issue-dialog.tsx — add import here) or similar

---

#### Step 6: Frontend — Wire dialog state in IssueDetail

**File**: `frontend/src/features/issues/components/issue-detail.tsx`
- Import `NewIssueDialog` (already a named export, no barrel file needed)
- Add `[newIssueOpen, setNewIssueOpen] = useState(false)` state
- Pass `onCreateFromHere={() => setNewIssueOpen(true)}` to `<IssueActions>`
- Render `<NewIssueDialog projectId={projectId} open={newIssueOpen} onOpenChange={setNewIssueOpen} sourceIssueId={issue.id} />` somewhere in the component tree (e.g., next to the delete confirmation dialog)

---

#### Step 7: Frontend — Optional: add a success toast note about auto-relation

**File**: `frontend/src/features/issues/components/new-issue-dialog.tsx`
- When `sourceIssueId` is provided, the success toast could say "Issue created (linked to source)" instead of just "Issue created"
- Or leave as-is — the relation tab on the new issue will show the link

### Data Flow

```
[Issue Detail Page]
  ├── IssueActions → button "Create issue from here" (visible for all statuses)
  │     └── onClick → onCreateFromHere callback
  ├── NewIssueDialog (open/close state managed by IssueDetail)
  │     └── onSubmit → POST /api/projects/{id}/issues
  │           ├── description, priority, category, tags
  │           └── source_issue_id: <current issue ID>
  └── Backend POST handler
        ├── IssueService.create() → creates issue record
        ├── IssueRelationService.add_relation(new_id, source_id, "related")
        │     └── Normalizes: sorts IDs for "related" type
        └── db.commit()
```

### Dependencies

- Task order: 1→2 (backend), 3→4→5→6 (frontend), 7 (optional). Backend and frontend can be done in any order, but within each side, follow the numbered order.
- No new database migrations needed
- No new models needed
- No new npm packages needed

### Risks & Mitigations

- **Risk**: IssueActions terminal-state guard prevents all rendering. **Mitigation**: Move the guard from early-return to conditional rendering — "Create from here" button always renders.
- **Risk**: Relation normalization could swap new/source order. **Mitigation**: Not a risk — normalization is correct behavior. The "related" relation stores both IDs symmetrically regardless of order.
- **Risk**: Relation creation fails after issue creation. **Mitigation**: Acceptable — the issue exists without a relation. No orphan data. Future retry via manual relation tab.
