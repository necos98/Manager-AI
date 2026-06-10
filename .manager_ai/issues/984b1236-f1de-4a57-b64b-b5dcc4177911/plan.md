# Piano: Breadcrumb Navigation Dinamico

## Task 1 — Creare il componente PageBreadcrumb
Creare `frontend/src/shared/components/page-breadcrumb.tsx`:

1. Importa `useLocation`, `useNavigate`, `Link` da `@tanstack/react-router`
2. Importa `useProject` da `@/features/projects/hooks`
3. Importa `useIssue` da `@/features/issues/hooks`
4. Importa `cn` da `@/shared/lib/utils`

Il componente:
- Legge `pathname` da `useLocation()`
- Splitta il pathname su `/`, filtra stringhe vuote
- Costruisce una lista di segmenti: ogni segmento ha label + path href
- Mappa i segmenti in base alla loro posizione:
  - Primo segmento vuoto → "Projects" → "/"
  - "projects" → non è un segmento mostrato (fa parte del pattern)
  - `$projectId` (UUID) → usa `useProject()` per ottenere il nome, mostra loading "..."
  - "issues" → "Issues"
  - `$issueId` (UUID) → usa `useIssue()` per ottenere issue.name, mostra loading "..."
  - Altri segmenti noti: "dashboard", "queue", "settings", "providers", "agents", "pipelines", "terminals", "questions", "library", "new", "archived" → mappati a etichette leggibili
  - Segmenti sconosciuti → capitalizzati (first letter uppercase, rest lower)
- Rende i segmenti come flex row con separatore `/` tra di loro
- L'ultimo segmento è testo semplice in bold
- I segmenti intermedi sono link `<Link>` di TanStack Router con testo muted-foreground e hover:text-foreground
- Tutti i segmenti tranne l'ultimo sono cliccabili
- Usa `className="truncate max-w-[200px]"` per limitare larghezza segmenti
- Wrap in un contenitore con `overflow-hidden` per responsive

## Task 2 — Integrare il Breadcrumb nel Root Layout
Modificare `frontend/src/routes/__root.tsx`:

1. Importare `PageBreadcrumb` dal nuovo componente
2. Aggiungere il breadcrumb nel div principale (`flex-1 flex flex-col`), tra l'header mobile e `<main>`
3. Renderizzato solo su schermi `md:` (classe `hidden md:flex`)
4. Posizionato con padding: `px-6 py-2` tra l'header mobile e il main
5. Aggiungere bordo inferiore sottile (`border-b`) per separare dal contenuto

## Verifica
- Aprire l'app in browser e navigare tra le pagine
- Verificare che il breadcrumb appaia correttamente su ogni rotta
- Verificare che i link funzionino correttamente
- Verificare che i nomi dei progetti e delle issue vengano risolti dinamicamente
- Verificare comportamento responsive (schermi stretti vs larghi)
