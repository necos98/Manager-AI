# Remove IssueStatus Transition Validators

## Overview
Remove the `VALID_TRANSITIONS` constraint from `IssueService.update_status()` so agents can transition issues between any status without validation errors.

## Scope
- **Remove** `VALID_TRANSITIONS` dict from `models/issue.py` (dead code)
- **Remove** transition check (`if (current, desired) not in VALID_TRANSITIONS`) from `update_status()` in `issue_service.py`
- **Remove** CANCELED special case in `update_status()` — redundant since all transitions become valid
- **Remove** `VALID_TRANSITIONS` from the import line in `issue_service.py` (keep `ALLOWED_CATEGORIES` and `IssueStatus`)
- **Remove** `InvalidTransitionError` from `update_status()` — no longer raised there
- **Update** `test_issue_model.py`: remove all tests that reference `VALID_TRANSITIONS` (lines 9-25)
- **Update** `test_issue_service.py`: remove `test_update_status_invalid_transition` (expects `InvalidTransitionError`); remove `test_update_status_canceled_from_any` (no longer a special case); keep `test_update_status_valid_transition` (it will still pass)
- **Update** `test_routers_issues.py`: remove `test_update_status_invalid` (expects 409 for New→Finished, which will now be valid); adjust `test_update_status_valid` docstring since Canceled is no longer a special case

## Constraints (DO NOT TOUCH)
The following state-machine checks are **explicitly out of scope** and must remain unchanged:
- `create_spec()` — checks issue is in NEW status
- `edit_spec()` — checks issue is in REASONING status
- `create_plan()` — checks issue is in REASONING status
- `edit_plan()` — checks issue is in PLANNED status
- `accept_issue()` — checks issue is in PLANNED status
- `complete_issue()` — checks issue is in ACCEPTED status and all tasks completed
- `InvalidTransitionError` exception class — still used by the above methods, must NOT be removed
- `cancel_issue()` method — independent from `update_status()`, stays as-is

## Acceptance Criteria
1. `update_status()` accepts **any** `IssueStatus` value from **any** current status — no `InvalidTransitionError` raised
2. `VALID_TRANSITIONS` removed from `models/issue.py`
3. `VALID_TRANSITIONS` removed from import in `issue_service.py`
4. CANCELED special case removed from `update_status()` body
5. `InvalidTransitionError` no longer raised by `update_status()`
6. All tests pass after test updates

## Non-Goals
- No changes to spec/plan/task lifecycle methods
- No changes to router layer (only test assertions)
- No changes to MCP tools
- No changes to `ALLOWED_CATEGORIES` or other model constants
- No changes to `InvalidTransitionError` exception class or its usage outside `update_status()`
- No changes to `cancel_issue()` method