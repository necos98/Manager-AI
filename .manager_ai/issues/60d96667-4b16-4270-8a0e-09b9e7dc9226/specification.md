# Dark Mode / Night Mode Specification

## Overview

Add full dark mode support to Manager AI frontend. The project already has `next-themes` installed, Tailwind v4 dark variant active (`@custom-variant dark (&:is(.dark *))`), and shadcn/ui components use `dark:` utilities throughout. The gap: no complete dark CSS variables, no ThemeProvider, no toggle.

## Scope

### Changes
1. **Complete `.dark` CSS variables** in `index.css` — shadcn default dark palette (neutral grays, oklch)
2. **Wrap app with ThemeProvider** from `next-themes` in `__root.tsx`
3. **Add theme toggle** (Sun/Moon icon button) in sidebar footer using `useTheme` from `next-themes`
4. **Fix Toaster theme** — make it dynamic based on current theme instead of hardcoded "system"

### Out of scope
- Per-component dark mode customizations (already handled by shadcn `dark:` utilities)
- Terminal themes (already have `TERMINAL_THEMES` selection)
- Dark mode for external plugins
- Backend changes

## Technical Design

### 1. CSS Variables (`frontend/src/index.css`)

Replace the incomplete `.dark` block (which only has sidebar vars) with the full shadcn default dark palette:

```css
.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.145 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.145 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.985 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.396 0.141 25.723);
  --destructive-foreground: oklch(0.637 0.237 25.331);
  --border: oklch(0.269 0 0);
  --input: oklch(0.269 0 0);
  --ring: oklch(0.439 0 0);
  --sidebar-background: oklch(0.145 0 0);
  --sidebar-foreground: oklch(0.985 0 0);
  --sidebar-primary: oklch(0.985 0 0);
  --sidebar-primary-foreground: oklch(0.205 0 0);
  --sidebar-accent: oklch(0.269 0 0);
  --sidebar-accent-foreground: oklch(0.985 0 0);
  --sidebar-border: oklch(0.269 0 0);
  --sidebar-ring: oklch(0.439 0 0);
}
```

### 2. ThemeProvider (`frontend/src/routes/__root.tsx`)

Wrap the app in `<ThemeProvider>` from `next-themes`:
- `attribute="class"` — toggles `.dark` class on `<html>` — matches Tailwind v4 `@custom-variant`
- `defaultTheme="system"` — respects OS preference
- `enableSystem` — allows system preference tracking
- `disableTransitionOnChange` — prevents flash during toggle

### 3. Theme Toggle (`frontend/src/shared/components/theme-toggle.tsx`)

New component using `useTheme` from `next-themes`:
- Sun icon when dark, Moon icon when light (or vice versa based on current mode)
- Renders in sidebar footer (replace current "Show on Smartphone" or place near it)
- Uses `Button` variant="ghost" size="icon"
- Calls `setTheme(theme === "dark" ? "light" : "dark")`

### 4. Toaster Fix (`frontend/src/routes/__root.tsx`)

Replace hardcoded `theme = "system"` with dynamic theme from `useTheme`. Extract Toaster into a child component of ThemeProvider so `useTheme` is available.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/index.css` | Complete `.dark` block with all dark variables |
| `frontend/src/routes/__root.tsx` | Add ThemeProvider wrapper, fix Toaster theme |
| `frontend/src/shared/components/theme-toggle.tsx` | New — theme toggle button component |
| `frontend/src/shared/components/app-sidebar.tsx` | Add ThemeToggle to sidebar footer |

## Dependencies

No new dependencies — `next-themes` v0.4.6 already in `package.json`.

## Verification

1. Toggle dark mode — all pages render correctly with dark background/foreground
2. System preference respected on first load
3. Preference persists across page refresh (localStorage)
4. No flash of light theme on dark mode page load
5. All shadcn components (buttons, inputs, dialogs, dropdowns, badges, tabs) adapt to dark
6. Sidebar renders correctly in both modes
7. Toaster notifications use correct theme
8. Terminal page unaffected (xterm uses its own themes)
