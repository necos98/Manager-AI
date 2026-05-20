## Summary

Fixed textarea horizontal overflow when pasting formatted text into the New Issue dialog.

## Root Cause

The shared `Textarea` component used `break-words` (`overflow-wrap: break-word`) which only breaks at soft wrap opportunities. Pasted text from external software (Word, Google Docs) often contains non-breaking spaces, long URLs, and zero-width characters that bypass this CSS property.

## Change

**File**: `frontend/src/shared/components/ui/textarea.tsx`

Three class changes:
- `break-words` → `overflow-wrap-anywhere` — breaks at any character boundary, no longer limited to soft wrap points
- Added `resize-y` — prevents horizontal resize drag, only vertical resize allowed
- Added `overflow-x-hidden` — safety net to hide any remaining overflow

One file changed, one line modified. Fix applies to all Textarea usages across the app, not just the New Issue dialog.