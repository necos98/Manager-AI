# Breadcrumb Navigation Dinamico

## Problema
Attualmente non c'è alcuna indicazione visiva della posizione nella gerarchia delle pagine. L'utente naviga tra Projects > Issues > Issue Detail senza sapere dove si trova.

## Obiettivo
Aggiungere un breadcrumb navigabile nell'header di ogni pagina che mostra il percorso gerarchico corrente.

## Specifica

### 1. Breadcrumb Component (`frontend/src/shared/components/page-breadcrumb.tsx`)
Un componente React che:
- Legge la route corrente da TanStack Router (`useLocation()`, `useMatches()`)
- Costruisce segmenti breadcrumb basati sul pathname
- Ogni segmento è cliccabile (link) per risalire la gerarchia
- Supporta etichette dinamiche per risorse (project name, issue name)

### 2. Route label mapping
Mappare pattern di route a etichette leggibili:
| Route pattern | Etichetta |
|---|---|
| `/` | Projects |
| `/dashboard` | Dashboard |
| `/projects/$projectId` | project.name |
| `/projects/$projectId/issues` | Issues |
| `/projects/$projectId/issues/$issueId` | issue.name |
| `/projects/$projectId/pipelines` | Pipelines |
| `/projects/$projectId/plugins` | Plugins |
| `/projects/$projectId/memories` | Memories |
| `/projects/$projectId/files` | Files (Uploaded) |
| `/projects/$projectId/commands` | Commands |
| `/projects/$projectId/variables` | Variables |
| `/projects/$projectId/activity` | Activity |
| `/projects/$projectId/health` | Health |
| `/projects/$projectId/ask` | Ask AI |
| `/projects/$projectId/library` | Library |
| `/projects/new` | New Project |
| `/projects/archived` | Archived |
| `/queue` | Issue Queue |
| `/settings` | Settings |
| `/providers` | Providers |
| `/agents` | Agents |
| `/pipelines` | Pipelines |
| `/terminals` | Terminals |
| `/questions` | Questions |
| `/library` | Library |

Per i segmenti dinamici (`$projectId`, `$issueId`), il componente deve usare le hook esistenti (`useProject`, `useIssue`) per risolvere i nomi. Mostra un placeholder "..." durante il loading.

### 3. Integrazione nel layout root
Inserire il breadcrumb in `frontend/src/routes/__root.tsx`:
- Renderizzato DENTRO il div principale (`flex-1 flex flex-col`), tra l'header mobile e `<main>`
- Visibile solo su schermi `md:` e superiori (su mobile lo spazio è prezioso e c'è già l'header)
- Posizionato sopra il contenuto principale come barra orizzontale fissa

### 4. Stile e accessibilità
- Padding verticale contenuto (py-2 px-6), testo small (text-sm)
- Separator: `/` (slash) tra i segmenti
- Segmento attivo (ultimo) in grassetto, colore foreground primario
- Segmenti intermedi in muted-foreground con hover effect
- Breadcrumb overflow: intermedi troncati con ellipsis su schermi stretti tramite CSS truncate
- Ogni segmento è un `<Link>` di TanStack Router tranne l'ultimo

### 5. Implementazione dettagliata
Il componente usa `useLocation()` per ottenere il pathname attuale e `useMatches()` per ottenere i parametri di rotta risolti. Costruisce i segmenti analizzando il pathname:
- Split su `/`
- Ogni segmento ha: label, path href, è_l'ultimo?
- Per i segmenti che sono parametri (projectId, issueId), usa le hook per risolvere il nome
- Rende con shadcn Badge o span + Separator

### Non incluso in questa issue
- Breadcrumb personalizzato per dashboard custom
- Breadcrumb con icone per segmento
- Animazioni transizione breadcrumb
