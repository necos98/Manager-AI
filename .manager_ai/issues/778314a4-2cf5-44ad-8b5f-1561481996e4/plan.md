# Implementation Plan: Attach project files to issues from the file gallery

## Summary

Single-file frontend change to `new-issue-dialog.tsx`. Add a "Browse Files" button that opens the existing `FileGalleryModal`. On file select, insert `@.manager_ai/resources/{stored_name}` at cursor position in the textarea.

## Files to modify

| File | Change |
|------|--------|
| `frontend/src/features/issues/components/new-issue-dialog.tsx` | Add gallery button, FileGalleryModal, cursor-aware text insertion |

No new files. No backend changes.

---

### Task 1: Add file gallery to NewIssueDialog

**Files:**
- Modify: `frontend/src/features/issues/components/new-issue-dialog.tsx`

**Steps:**

- [ ] **Step 1: Add imports and state**

Add imports for `useRef`, `useCallback`, `FileGalleryModal`, `ProjectFile`, and `Paperclip` icon (from lucide-react).

Add state:
```tsx
const [galleryOpen, setGalleryOpen] = useState(false);
const textareaRef = useRef<HTMLTextAreaElement>(null);
```

- [ ] **Step 2: Add cursor-aware insertion handler**

```tsx
const handleFileSelect = useCallback((file: ProjectFile) => {
  const tag = `@.manager_ai/resources/${file.stored_name} `;
  const textarea = textareaRef.current;
  if (textarea) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    setDescription((prev) => prev.slice(0, start) + tag + prev.slice(end));
    // Restore cursor after inserted tag
    requestAnimationFrame(() => {
      const newPos = start + tag.length;
      textarea.selectionStart = newPos;
      textarea.selectionEnd = newPos;
      textarea.focus();
    });
  } else {
    setDescription((prev) => prev + tag);
  }
  setGalleryOpen(false);
}, []);
```

- [ ] **Step 3: Add Browse Files button below textarea**

Add after the character count line (before the Priority section):
```tsx
<Button
  type="button"
  variant="outline"
  size="sm"
  onClick={() => setGalleryOpen(true)}
>
  <Paperclip className="size-4 mr-2" />
  Browse Files
</Button>
```

- [ ] **Step 4: Wire Textarea ref**

Change the Textarea to use the ref:
```tsx
<Textarea
  id="new-issue-description"
  ref={textareaRef}
  ...
/>
```

Note: The current `Textarea` component from shadcn/ui uses `React.forwardRef`, so it accepts a ref natively.

- [ ] **Step 5: Add FileGalleryModal at end of dialog**

Add just before the closing `</Dialog>` tag:
```tsx
<FileGalleryModal
  open={galleryOpen}
  onClose={() => setGalleryOpen(false)}
  projectId={projectId}
  onSelect={handleFileSelect}
/>
```

- [ ] **Step 6: Verify**
  - `npm run lint` passes
  - `npm run dev` — open New Issue dialog, click Browse Files, select a file, verify tag inserted at cursor
  - Test cursor at different positions (start, middle, end, with selection)
