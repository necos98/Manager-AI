## Problem

When users paste text from external software (Word, Google Docs, etc.) into the New Issue description textarea, the textarea expands horizontally beyond the dialog boundaries, hiding the Create button and making it impossible to submit.

## Root Cause

The `Textarea` component at `frontend/src/shared/components/ui/textarea.tsx` uses `break-words` (`overflow-wrap: break-word`) which only breaks at soft wrap opportunities. Pasted content from external sources can contain:

1. **Non-breaking spaces** (` `) — treated as non-breakable characters by CSS
2. **Long unbroken strings** — URLs, code snippets, paths
3. **Zero-width characters** — prevent line breaking

These characters bypass `overflow-wrap: break-word`, causing the textarea to stretch horizontally.

## Solution

Modify the shared `Textarea` component's CSS classes to enforce wrapping at any character boundary.

### Changes

**File**: `frontend/src/shared/components/ui/textarea.tsx`

Replace `break-words` with `overflow-wrap-anywhere` (Tailwind v4), and add `resize-y` + `overflow-x-hidden`:

- `overflow-wrap-anywhere` — breaks at any character, including non-breaking spaces and long strings
- `resize-y` — prevents user from dragging textarea wider horizontally; vertical resize still allowed
- `overflow-x-hidden` — safety net: hides any remaining overflow instead of expanding container

### Affected Files

| File | Change |
|------|--------|
| `frontend/src/shared/components/ui/textarea.tsx` | Update className on `<textarea>` element |

### Non-goals

- Paste event sanitization (not needed with correct CSS)
- New Issue dialog changes (fix is at shared component level)
