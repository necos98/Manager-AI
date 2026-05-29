# Implementation Plan: Enable Text Selection/Copy in Tabs

## Overview

Two independent changes to the frontend: (1) guard InlineEditField onClick against active text selections, (2) add copy-to-clipboard buttons to code blocks in MarkdownViewer. No backend, CSS, or dependency changes.

---

## Change 1: InlineEditField selection guard

**File:** `frontend/src/features/issues/components/inline-edit-field.tsx`

**What:** At line 126, the `onClick` handler unconditionally calls `setEditing(true)` even when the user has selected text. Change it to check `window.getSelection().toString()` first.

**Details:**
- Line 126: `onClick={() => !disabled && setEditing(true)}`
- New behavior: `onClick={() => { if (!disabled && !window.getSelection()?.toString()) setEditing(true); }}`
- If user has selected text, click does nothing → selection preserved
- If no selection, click enters edit mode as before
- Applies uniformly to all 3 InlineEditField usages (name line 107, priority line 115, description line 234) since they all use the same component instance pattern

**Edge case:** User selects text outside the field then clicks inside → `getSelection()` is non-empty → edit mode blocked. Acceptable trade-off per SpecReviewer.

---

## Change 2: MarkdownViewer code block copy button

**File:** `frontend/src/shared/components/markdown-viewer.tsx`

**What:** Add a custom `code` component renderer to ReactMarkdown's `components` prop. For fenced code blocks (where the `className` starts with `language-`), render a `<pre>` wrapper with an overlay copy button.

**Details:**
- Import `Copy` icon from `lucide-react`
- Add a `components` prop to `<ReactMarkdown>` with a custom `code` renderer
- The renderer checks if this is a fenced block (has `className` matching `language-*`) vs inline code (no class or no `children` as array)
- For fenced blocks, render a `<pre>` wrapper with the existing `<code>` element plus an absolute-positioned copy button in top-right
- Copy button calls `navigator.clipboard.writeText()` with `String(children).trim()` (removes trailing `\n`)
- Copy button includes `e.stopPropagation()` so click doesn't bubble to parent InlineEditField
- Button styled with `opacity-0 group-hover:opacity-100` to appear on hover only

**Key decisions:**
- No new npm dependencies — using `navigator.clipboard` and lucide-react (already in project)
- Inline code `<code>` without `<pre>` gets no copy button per spec
- Copy button uses `group-hover` pattern: wrapper is `group`, button is initially invisible, shows on wrapper hover
- Button positioned absolutely top-right inside the `pre` wrapper

---

## Implementation order

1. **InlineEditField** — simpler change, no visual design decisions
2. **MarkdownViewer** — needs visual layout (copy button position, hover behavior)

---

## Files changed

- `frontend/src/features/issues/components/inline-edit-field.tsx` — 1-line change to onClick
- `frontend/src/shared/components/markdown-viewer.tsx` — add custom code renderer + import

## Files NOT changed (confirmed by codebase exploration)

- `frontend/src/features/issues/components/issue-detail.tsx` — structure fine
- `frontend/src/shared/components/ui/card.tsx` — no selection blocking
- `frontend/src/shared/components/ui/tabs.tsx` — no selection blocking
- `start.py` — no injected CSS blocking selection
- No CSS files, no backend files, no config files

## Verification

1. Open any issue detail page
2. Try to select text in the Description tab — click should NOT enter edit mode when text is selected
3. Click Description without selection — should enter edit mode normally
4. Verify issue name and priority inline edit still work
5. View spec/plan/recap tabs with markdown containing code blocks — copy button appears on hover
6. Click copy button — content goes to clipboard, no unwanted edit mode activation
