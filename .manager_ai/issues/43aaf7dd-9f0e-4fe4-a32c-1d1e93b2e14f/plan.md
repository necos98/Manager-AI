# Implementation Plan

## Files

- **Modify**: `frontend/src/shared/components/ui/textarea.tsx` — add `break-words` to className

## Task 1: Add `break-words` to Textarea component

Add the Tailwind `break-words` utility to the shared `Textarea` component's className. This applies `overflow-wrap: break-word`, causing long unbroken strings (URLs) to wrap at the textarea boundary.

### Steps

1. Edit `frontend/src/shared/components/ui/textarea.tsx` — add `break-words` to the className array on line 10
2. Verify the change compiles: `cd frontend && npm run build` (or `npx tsc --noEmit`)
3. Visual verification: paste a long URL into the New Issue modal textarea, confirm it wraps within the modal