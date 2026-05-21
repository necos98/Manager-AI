## Changes Made

### 1. `frontend/src/index.css`
Replaced incomplete `.dark` block (only 7 sidebar variables) with full shadcn default dark palette — 27 CSS custom properties in oklch color space. All variables now defined: background, foreground, card, popover, primary, secondary, muted, accent, destructive, border, input, ring, and all sidebar variants.

### 2. `frontend/src/routes/__root.tsx`
- Added import of `ThemeProvider` and `useTheme` from `next-themes`
- Wrapped app in `<ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>`
- Extracted `ThemeToaster` component that reads theme from `useTheme` and passes it to Sonner's `<Toaster>`

### 3. `frontend/src/shared/components/theme-toggle.tsx` (new)
Theme toggle button using `useTheme` from `next-themes` with Moon/Sun icons from `lucide-react`. Handles hydration mismatch with `mounted` state pattern (renders disabled placeholder until mounted).

### 4. `frontend/src/shared/components/app-sidebar.tsx`
Added `<ThemeToggle />` to sidebar footer as a second menu item below "Show on Smartphone".

## Key Details
- No new dependencies — `next-themes` v0.4.6 was already in `package.json`
- Tailwind v4 dark variant (`@custom-variant dark (&:is(.dark *))`) was already active
- shadcn/ui components already use `dark:` utilities throughout — they now work correctly with the completed CSS variables
- Build verified: 2767 modules, zero errors, production build 5.64s
