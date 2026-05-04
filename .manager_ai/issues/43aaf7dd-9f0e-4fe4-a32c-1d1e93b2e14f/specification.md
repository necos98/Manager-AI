# Fix New Issue modal textarea overflow when pasting links

## Problem

When pasting long URLs (or any continuous unbroken string) into the New Issue modal's textarea, the text overflows horizontally beyond the modal boundary. The textarea element has `w-full` but no word-breaking, so browsers can't find a break point in continuous strings like URLs.

## Root cause

`frontend/src/shared/components/ui/textarea.tsx` — the shared `Textarea` component lacks `overflow-wrap: break-word`. Long unbroken strings (URLs) overflow the element and the dialog.

## Fix

Add the Tailwind `break-words` utility class to the `Textarea` component's className.

- **File**: `frontend/src/shared/components/ui/textarea.tsx`
- **Change**: Add `break-words` to the className array (line 10)
- **Effect**: Long URLs and unbroken strings wrap at the textarea boundary instead of overflowing. Applied globally to all textarea instances.
- **Risk**: None. `overflow-wrap: break-word` is standard behavior for textareas and only affects rendering of long unbroken strings.

## Acceptance criteria

1. Paste a long URL (200+ chars, no spaces) into the New Issue modal textarea — text wraps within the modal boundary
2. All other textarea usages continue to work correctly
3. Normal text entry (with spaces) behavior is unchanged