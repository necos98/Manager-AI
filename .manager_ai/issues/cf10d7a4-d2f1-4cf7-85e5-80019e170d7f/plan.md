## Implementation Plan: Badge visuale "In Queue" nella Issue Detail Page

### Task 1: Importare useQueuePosition hook in IssueDetail.tsx
Aggiungere l'import di `useQueuePosition` da `@/features/queue/hooks` nel file `issue-detail.tsx`.

### Task 2: Chiamare useQueuePosition nel componente IssueDetail
In IssueDetail, chiamare `const { data: queuePosition } = useQueuePosition(issue.id, projectId);` e usare `queuePosition?.in_queue` e `queuePosition?.position` per decidere se e cosa mostrare.

### Task 3: Aggiungere badge "In Queue" nell'header
Nella sezione header di IssueDetail (dopo StatusBadge), aggiungere un badge condizionale:
- Se `queuePosition?.in_queue === true`, renderizzare un Badge outline con colori ambra e testo "In Queue (#pos)"

### Task 4: Verifica
Compilare il frontend (npm run build o tsc --noEmit) per verificare che non ci siano errori di tipo o import mancanti.
