# Dark Mode Implementation Plan

**Goal:** Complete the existing dark mode infrastructure by adding CSS variables, ThemeProvider, toggle button, and dynamic Toaster theme.

**Architecture:** Use `next-themes` (already installed) to manage `.dark` class on `<html>`. Tailwind v4 dark variant already configured. shadcn/ui components already use `dark:` utilities. Only gap: missing dark CSS variables + ThemeProvider + toggle.

**Tech Stack:** React 19, Tailwind v4, next-themes v0.4.6, shadcn/ui, lucide-react

---

## Files

| File | Action |
|------|--------|
| `frontend/src/index.css` | Modify — replace incomplete `.dark` block with full palette |
| `frontend/src/routes/__root.tsx` | Modify — add ThemeProvider, fix Toaster theme |
| `frontend/src/shared/components/theme-toggle.tsx` | Create — mode toggle button |
| `frontend/src/shared/components/app-sidebar.tsx` | Modify — add ThemeToggle to footer |

## Implementation Steps

1. Add full dark CSS custom properties to `.dark` block in `index.css`
2. Wrap app in `<ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>` in `__root.tsx`
3. Create `ThemeToggle` component using `useTheme` from next-themes with Sun/Moon icons
4. Place `ThemeToggle` in sidebar footer
5. Extract Toaster into child of ThemeProvider, use dynamic theme from `useTheme`
6. Verify dark mode toggle works across pages
