# Attach project files to issues from the file gallery

## Summary

Add a "Browse Files" button to the New Issue dialog that opens the existing file gallery modal. When the user clicks a file, its reference path (`@.manager_ai/resources/{stored_name}`) is inserted into the description textarea at cursor position.

## Motivation

Users want to reference project files when creating issues (specs, screenshots, docs). The file gallery already supports selecting files to insert paths into the terminal — this extends the same pattern to the issue description textarea.

## Design

### Scope

- **Frontend only** — no backend changes, no API changes, no data model changes
- **Reuses** `FileGalleryModal` component and `@.manager_ai/resources/{stored_name}` reference format
- **Creation only for now** — edit support can follow later

### Changes

#### `frontend/src/features/issues/components/new-issue-dialog.tsx`

1. Import `FileGalleryModal` and `ProjectFile` type
2. Add `galleryOpen` state (boolean, default false)
3. Add `textareaRef` to track cursor position for insertion
4. Add "Browse Files" button below the textarea (secondary/outline variant, `Paperclip` or `FolderOpen` icon)
5. Render `<FileGalleryModal>` — on file select:
   - Get `textareaRef.current.selectionStart`
   - Insert `@.manager_ai/resources/{file.stored_name} ` at cursor
   - Restore cursor after inserted text
   - Close gallery
6. Also support Ctrl+V paste in dialog for direct uploads (already handled by `FileGalleryModal`)

### Reference format

```
@.manager_ai/resources/{file.stored_name}
```

Same format used by terminal panel (`terminal-panel.tsx:81`) and global image paste (`use-global-image-paste.ts:51`). Claude already resolves `@` paths when reading the issue description.

### UI layout

```
┌─────────────────────────────────────┐
│  New Issue                          │
│                                     │
│  Description *                      │
│  ┌─────────────────────────────────┐│
│  │ (textarea)                      ││
│  │                                 ││
│  └─────────────────────────────────┘│
│  12 / 50,000                        │
│  [📁 Browse Files]                  │
│                                     │
│  Priority                           │
│  [3                  ▾]             │
│                                     │
│  ⌘↵ to submit    [Cancel] [Create]  │
└─────────────────────────────────────┘
```

### Behavior

- Click "Browse Files" → opens `FileGalleryModal` (full modal with upload, grid, filters)
- Click a file in gallery → tag inserted at cursor, gallery closes, focus returns to textarea
- User can insert multiple files by reopening the gallery
- Existing paste/drop in gallery works for uploading new files
