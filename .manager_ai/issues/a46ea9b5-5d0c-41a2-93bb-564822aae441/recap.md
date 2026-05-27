## Changes Made

### Backend
- Added `project_name` and `issue_name` optional fields to `QuestionResponse` schema (`backend/app/schemas/question.py`)
- Updated `get_all()` in `QuestionService` to use LEFT JOINs on `issues` and `projects` tables, attaching names as dynamic attributes on Question objects
- Updated `get_pending()` to batch-resolve project/issue names from DB for in-memory QuestionStore objects

### Frontend
- Added `project_name` and `issue_name` optional fields to `Question` TypeScript interface
- Rewrote `QuestionCard` component to include:
  - Color-coded status badge (amber=pending, green=answered, gray=timed_out)
  - Project name as muted text
  - Clickable issue name linking to the issue detail page via TanStack Router Link
  - Relative timestamps using `date-fns` formatDistanceToNow ("Asked X ago", "Answered X ago")

### Verification
- 551 backend tests pass (34 pre-existing failures in unrelated tests)
- TypeScript compilation clean (no errors)