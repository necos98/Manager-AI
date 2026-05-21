## Files

| Action | File |
|--------|------|
| Modify | `frontend/src/shared/components/ui/textarea.tsx` |

## Implementation

### Task 1: Update Textarea CSS classes

**File**: `frontend/src/shared/components/ui/textarea.tsx`

Replace `break-words` with `overflow-wrap-anywhere`, add `resize-y` and `overflow-x-hidden` to the `<textarea>` className.

**Current line 10:**
```tsx
"flex field-sizing-content min-h-16 w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:aria-invalid:ring-destructive/40 break-words",
```

**Change to:**
```tsx
"flex field-sizing-content min-h-16 w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:aria-invalid:ring-destructive/40 overflow-wrap-anywhere resize-y overflow-x-hidden",
```

**What changes and why:**
- `break-words` → `overflow-wrap-anywhere`: `break-words` only breaks at soft wrap opportunities. `overflow-wrap-anywhere` breaks at any character — handles non-breaking spaces, long URLs, pasted rich-text artifacts.
- `resize-y`: Prevents user from dragging textarea horizontally, which also causes overflow. Vertical resize remains.
- `overflow-x-hidden`: Safety net — if content still overflows, hide the scrollbar instead of expanding container.

### Verification

1. Start the app: `python start.py`
2. Navigate to a project's Issues page
3. Click "New Issue"
4. Paste text from Word / Google Docs with non-breaking spaces and long URLs
5. Confirm textarea wraps correctly, no horizontal overflow
6. Confirm Create button remains visible and clickable
7. Verify textarea still works in other places (settings, terminal commands, project settings)
