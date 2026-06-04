## Overview

Add a "Create issue from here" button on the issue detail page. Users with a finished/canceled issue can spawn a new issue linked to it — preserving context and traceability without manual re-linking.

## User Story

> As a user, when viewing any issue (including finished/canceled ones), I want to click a button that opens the new-issue dialog. After I fill in the description and create, the new issue is automatically linked as "related" to the source issue — no manual relation setup needed.

## Scope

### In scope

1. **Button** — "Create issue from here" in the IssueActions action bar on the issue detail page
2. **Dialog** — reuse existing `NewIssueDialog` component with same fields (description, priority, tags, category)
3. **Auto-relation** — after creation, a "related" relation is established from the new issue to the source issue
4. **Visibility** — button shows for ALL issue statuses, including Finished and Canceled
5. **Backend** — accept `source_issue_id` in `IssueCreate` schema, create relation automatically after issue creation

### Out of scope (non-goals)

- Pre-filling fields from the source issue (description, tags, etc.)
- Batch creation or multi-select
- New relation types — only "related"
- Changes to issue edit/update flows
- Changes to relation display or management UI

## Constraints

1. Source issue may be in any status (including Finished/Canceled) — button must not be hidden by existing status-based visibility logic
2. "related" relation follows the project's existing bidirectional convention (sorted IDs) — only create one direction
3. Relation cache on the source issue's YAML must invalidate after creation
4. `NewIssueDialog` currently only exists on the issues list page — must be importable from the detail page without duplication

## Acceptance Criteria

1. Button "Create issue from here" is visible in the action bar on every issue detail page, regardless of issue status
2. Clicking the button opens `NewIssueDialog` with all standard fields available
3. Creating the issue succeeds with standard validation
4. The new issue has a "related" relation pointing to the source issue
5. The source issue's relation list (YAML) includes the new issue's ID
6. No regressions in issue creation from the list page

## Technical Context

**Relationship model**: Issues store relations in `.manager_ai/issues/<id>/index.yaml` under a `relations:` key. Each relation has a `target_id` and `type` string. Relations are bidirectional by convention — IDs are sorted lexicographically to determine canonical order.

**IssueActions component**: Located at `features/issues/components/issue-actions.tsx`. Currently conditionally renders based on issue status — "Create from here" should bypass this filter.

**NewIssueDialog component**: Located at `features/issues/components/new-issue-dialog.tsx`. Needs to accept an optional `sourceIssueId` prop that gets sent to the API as `source_issue_id`.