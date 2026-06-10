## Quick-create issue dalla sidebar

**Problema:** Il pulsante "New Issue" è visibile solo nella pagina Issues del progetto. Per creare una issue devi essere su quella pagina, interrompendo il flusso di lavoro.

**Obiettivo:** Aggiungere un pulsante "Quick Create" accessibile globalmente dalla sidebar o via shortcut.

**Cosa fare:**
1. Pulsante "+" nella ProjectSidebar accanto al nome del progetto
2. Alla pressione: apre un modal ridotto di creazione (solo description + priority)
3. Opzionale: shortcut `n` per aprire ovunque
4. Mantenere il modal full per creazione avanzata
5. Il modal quick ha solo: textarea, priority select, pulsante Create

**File interessati:**
- `src/shared/components/project-sidebar.tsx`
- `src/features/issues/components/new-issue-dialog.tsx` (creare versione quick o parametrizzare)

**Priorità:** Alta — riduce i click per operazione frequente