## Bulk actions su Kanban board

**Problema:** Non è possibile selezionare più issue per operazioni bulk (cambio status, assegnazione tag, cancellazione). Ogni operazione richiede di agire su una issue alla volta.

**Obiettivo:** Aggiungere modalità selezione multipla sulla Kanban board con action bar.

**Cosa fare:**
1. Checkbox su ogni kanban card (visibile in "select mode")
2. Pulsante "Select" nella toolbar che attiva la modalità
3. Action bar che compare quando 1+ card sono selezionate
4. Azioni bulk supportate:
   - Change status (con validazione transizioni)
   - Assign tags
   - Delete (con conferma)
   - Change priority
   - Change category
5. "Select all in column" e "Deselect all"

**File interessati:**
- `src/features/issues/components/kanban-board.tsx`
- `src/features/issues/components/kanban-card.tsx`
- Nuovo: `src/features/issues/components/bulk-action-bar.tsx`

**Priorità:** Alta — richiesta comune in tool di project management