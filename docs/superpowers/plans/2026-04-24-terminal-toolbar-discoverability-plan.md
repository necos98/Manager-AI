# Terminal Toolbar Discoverability — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans

**Goal:** Make terminal toolbar buttons more visible by increasing size and contrast.

**Architecture:** Single-file visual change in `terminal-panel.tsx`. Toolbar container background and button sizes/colors adjusted. No behavior change.

**Tech Stack:** React, Tailwind CSS, Lucide icons.

---

### Task 1: Update toolbar container and button styles

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx:277-334`

- [ ] **Step 1: Update toolbar container background**

Change line ~277 from:
```jsx
<div className="flex items-center justify-end gap-1 px-2 py-1 bg-zinc-900 border-b border-zinc-800">
```
To:
```jsx
<div className="flex items-center justify-end gap-1 px-2 py-1 bg-zinc-800/40 border-b border-zinc-700">
```

- [ ] **Step 2: Update all toolbar Button props**

For each of the 5 buttons (Files, Voice, Copy, Search, Log), change:
- `h-6` → `h-8`
- `text-zinc-400` → `text-zinc-200`

Buttons are at lines ~278-333. Key props to change:
- Files button (line 281): `h-6 text-xs text-zinc-400` → `h-8 text-xs text-zinc-200`
- Voice button (line 292): same
- Copy button (line 303): same
- Search button (line 314): same
- Log button (line 325): same

- [ ] **Step 3: Verify visually**

Run frontend (`npm run dev`) and confirm toolbar is more visible but not overwhelming.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/terminals/components/terminal-panel.tsx
git commit -m "feat(terminals): improve toolbar button visibility
- Increase button height h-6 → h-8
- Brighten text zinc-400 → zinc-200
- Subtle toolbar background tint"
```
