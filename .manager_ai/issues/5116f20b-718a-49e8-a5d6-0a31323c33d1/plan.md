# Implementation Plan: Remove IssueStatus Transition Validators

## Overview
Remove `VALID_TRANSITIONS` constraint from `update_status()` so agents can set any status without validation errors. 5 files touched, ~30 lines deleted total.

## Files to Change

### 1. `backend/app/models/issue.py` — Remove dead constant
- Delete `VALID_TRANSITIONS` dict (lines 21-26)
- Keep: `IssueStatus` enum, `ALLOWED_CATEGORIES`, `Issue` class — untouched

### 2. `backend/app/services/issue_service.py` — Simplify update_status()
- Update import: remove `VALID_TRANSITIONS` from line 22
- Rewrite `update_status()` (lines 174-196): remove CANCELED special case, remove VALID_TRANSITIONS check. New method just sets status directly without validation. No `InvalidTransitionError` raised.
- Keep: all other methods (create_spec, edit_spec, create_plan, edit_plan, accept_issue, complete_issue, cancel_issue, force_finish_issue) — untouched

### 3. `backend/tests/test_issue_model.py` — Remove VALID_TRANSITIONS tests
- Remove import of `VALID_TRANSITIONS` from line 1
- Remove 3 test functions: `test_valid_transitions_include_new_to_reasoning`, `test_valid_transitions_do_not_include_declined`, `test_all_expected_transitions_present` (lines 9-25)
- Keep: `test_declined_not_in_status_enum` — untouched

### 4. `backend/tests/test_issue_service.py` — Remove invalid transition + canceled tests
- Remove `test_update_status_invalid_transition` (lines 68-72) — no longer raises InvalidTransitionError
- Remove `test_update_status_canceled_from_any` (lines 75-79) — CANCELED no longer a special case
- Keep: `test_update_status_valid_transition` — will still pass

### 5. `backend/tests/test_routers_issues.py` — Remove invalid router test
- Remove `test_update_status_invalid` (lines 105-115) — expects 409, now returns 200
- Update docstring on `test_update_status_valid` line 92 from "any state can be Canceled" to "update_status accepts any transition"

## Execution Order
All edits are independent (different files). Can be done in any order.

## Verification
Run `python -m pytest` from `backend/` to confirm all tests pass.
