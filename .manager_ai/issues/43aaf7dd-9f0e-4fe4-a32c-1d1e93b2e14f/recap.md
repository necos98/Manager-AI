Added `break-words` Tailwind utility to the shared `Textarea` component (`frontend/src/shared/components/ui/textarea.tsx`). This applies `overflow-wrap: break-word`, causing long unbroken strings (URLs, paths) to wrap at the textarea boundary instead of overflowing horizontally past the modal edge.

**Change**: One class added to className array on line 10 of textarea.tsx.
**Build**: Verified — production build succeeds.