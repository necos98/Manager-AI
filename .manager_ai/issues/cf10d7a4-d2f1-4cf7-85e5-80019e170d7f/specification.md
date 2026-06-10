## Aggiungere badge visuale "In Queue" nella issue detail page

### Problema
Quando un utente aggiunge una issue alla coda (tramite il pulsante "Add to Queue" nella IssueActions bar), non c'è alcun feedback visivo nella sezione superiore della Issue Detail Page che indichi chiaramente che la issue è in coda. L'unico indicatore è il pulsante "Remove from Queue (#pos)" nella action bar, ma non è abbastanza visibile nell'header della pagina.

### Obiettivo
Aggiungere un badge visuale nella sezione header della Issue Detail Page (vicino allo StatusBadge) che indichi "In Queue (#pos)" quando la issue è in coda.

### Specifica tecnica

**File da modificare:** `frontend/src/features/issues/components/issue-detail.tsx`

**Modifiche:**
1. Importare il hook `useQueuePosition` da `@/features/queue/hooks`
2. Chiamare `useQueuePosition(issue.id, projectId)` nel componente `IssueDetail`
3. Nella sezione header (righe 133–138, dove vengono renderizzati StatusBadge, Pipeline badge, Select categoria, tags), aggiungere un badge condizionale dopo `StatusBadge`:
   - Se la issue è in coda (`queuePosition?.in_queue === true`), mostrare un Badge con variante outline e colori ambrati (simile a `"bg-amber-50 text-amber-700 border-amber-200 text-xs"`) con testo `"In Queue (#pos)"` dove `pos` è `queuePosition?.position`
   - Il badge deve essere visibile per **qualsiasi status** della issue (non solo New/Accepted), perché una volta in coda l'utente deve vederlo indipendentemente dallo stato

**Stile del badge:**
- Stessa dimensione del badge Pipeline esistente
- Colori ambra per distinguerlo dagli altri badge
- bordo ambra chiaro
- Testo "In Queue" con posizione in parentesi: es. "In Queue (#3)"

**Casi d'uso:**
- Issue in coda: mostra badge "In Queue (#pos)"
- Issue non in coda: nessun badge (non mostrare nulla)
- Stato loading del queue position: nessun badge (aspetta che i dati siano caricati)
