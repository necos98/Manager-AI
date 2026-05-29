# Enable Text Selection and Copy in Spec, Plan, and Content Tabs

## Description

Users cannot reliably select and copy text from the spec, plan, and other markdown-rendered content tabs. Investigation shows two distinct problems: (1) the InlineEditField component enters edit mode on any click, destroying text selections, and (2) code blocks rendered by MarkdownViewer lack copy-to-clipboard buttons.

## Scope

Two independent changes to the frontend:

### 1. InlineEditField — Preserve text selection on click

**File:** `frontend/src/features/issues/components/inline-edit-field.tsx`

**Current behavior:** The `onClick` handler at line ~126 calls `setEditing(true)` on every click — even when the user is trying to select text. The edit mode replaces the read-only view with an input field, destroying any text selection.

**Required behavior:** Before entering edit mode, check if the user has selected text. If `window.getSelection().toString()` is non-empty, treat the click as a selection action, NOT an edit action. Only enter edit mode on clicks without an active text selection.

**Constraint:** This component is also used for the issue name (line ~107) and priority display (line ~115). The fix must not break edit behavior for those cases — they should continue working exactly as before.

### 2. MarkdownViewer — Add copy button to code blocks

**File:** `frontend/src/shared/components/markdown-viewer.tsx`

**Current behavior:** `ReactMarkdown` renders `<pre><code>` with no way to copy code block content.

**Required behavior:** Add a custom `code` component renderer in the `components` prop passed to `ReactMarkdown`. For fenced code blocks (`<pre>` wrapping), render a small copy button in the top-right corner. On click, copy the code block text to clipboard via `navigator.clipboard.writeText()`.

**Constraint:** Do not add new npm dependencies — use `navigator.clipboard.writeText()` which is available in all modern browsers including the PyWebView wrapper. The copy button must not interfere with text selection of the code block content.

**Not in scope:** Adding copy buttons to inline code (single backtick `<code>` without `<pre>` parent).

## Acceptance Criteria

1. Clicking inside the Description tab (InlineEditField) to select text does NOT enter edit mode when text is selected
2. Clicking inside the Description tab without selecting text STILL enters edit mode (existing behavior preserved)
3. Issue name and priority InlineEditField usages continue to work unchanged
4. All markdown-rendered tabs (spec, plan, recap, notes) show a copy button on fenced code blocks
5. Clicking the copy button copies the code block content to clipboard
6. The copy button does not prevent text selection of code block content

## Non-goals

- Spec/plan/recap tabs do NOT need text selection fixes — they already allow selection (no CSS blocking)
- No third-party clipboard libraries
- No changes to Card, Tabs, or other UI components
- No backend changes
- No changes to `start.py`, CSS files, or layout

## Rationale

The user requested the ability to copy text from content tabs. Investigation identified two real blockers plus one non-issue. The spec/plan/recap tabs already allow text selection since they render MarkdownViewer directly. Only the Description tab (wrapped in InlineEditField) blocks selection because the click handler is too aggressive.
