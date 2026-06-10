## Recap: Badge visuale "In Queue" nella Issue Detail Page

### Modifiche effettuate

**File modificato:** `frontend/src/features/issues/components/issue-detail.tsx`

1. **Import aggiunto:** `useQueuePosition` da `@/features/queue/hooks`
2. **Hook chiamato** nel componente IssueDetail: `const { data: queuePosition } = useQueuePosition(issue.id, projectId);`
3. **Badge "In Queue (#pos)"** aggiunto nell'header della pagina, dopo StatusBadge e Pipeline badge:
   - Stile: `Badge variant="outline"` con colori ambra (`bg-amber-50 text-amber-700 border-amber-200`)
   - Visibile per qualsiasi status della issue quando `queuePosition?.in_queue === true`
   - Testo: "In Queue (#position)"

### Verifica
- TypeScript compilation (`npx tsc --noEmit`): passata senza errori
- Il badge è inserito subito dopo il badge Pipeline esistente, mantenendo coerenza visiva con gli altri badge nell'header

### Note
- Il badge si basa sullo stesso hook `useQueuePosition` già usato da `IssueActions` per il pulsante "Add to Queue"/"Remove from Queue", quindi non introduce nuove API o chiamate di rete
- Il badge è visibile per **tutti gli status**, non solo New/Accepted. Questo è corretto perché una volta che una issue è in coda, l'utente deve vedere l'indicatore indipendentemente dallo stato della issue