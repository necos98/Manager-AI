## Summary

Added a "Browse Files" button to the New Issue dialog that opens the existing `FileGalleryModal`. Selecting a file inserts its reference path (`@.manager_ai/resources/{stored_name}`) at the cursor position in the description textarea.

## Changes

**Modified:** `frontend/src/features/issues/components/new-issue-dialog.tsx`
- Added imports: `useCallback`, `useRef`, `Paperclip`, `FileGalleryModal`, `ProjectFile`
- Added `galleryOpen` state and `textareaRef` ref
- Added `handleFileSelect` callback: inserts `@.manager_ai/resources/{stored_name} ` at cursor position, restores cursor via `requestAnimationFrame`
- Added "Browse Files" outline button below textarea with `Paperclip` icon
- Wired `textareaRef` to the Textarea component
- Rendered `FileGalleryModal` at the end of the dialog

No backend changes. No new files. No data model changes.

## Verification

- TypeScript type check: passed (0 errors)
- Vite production build: passed (2754 modules, 0 errors)
- Manual testing: open New Issue dialog → click Browse Files → select file → tag inserted at cursor
