## Sidebar collassabile icon-only

**Problema:** ProjectSidebar + AppSidebar = 440px fissi di navigazione. Su 1366px ~32% spazio sprecato.

**Obiettivo:** Sidebar collassabili a icon-only (pattern VSCode/Linear).

**Cosa fare:**
1. Pulsante collapse in ogni sidebar
2. Stato salvato in localStorage
3. In modalita icon-only: solo icone, label nascosti
4. Tooltip al hover per mostrare nome
5. Transizione fluida

**File:** `app-sidebar.tsx`, `project-sidebar.tsx`, `ui/sidebar.tsx`