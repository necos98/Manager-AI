# Fase 7 — Galleria File & Paste Immagini

## Obiettivo

Permettere all'utente di caricare e incollare immagini (e altri file) in modo rapido mentre chatta con Claude Code nel terminale integrato. Claude deve poter "vedere" le immagini referenziate tramite tag `@path` nel prompt, sfruttando il supporto nativo di Claude Code CLI per i path file.

## Vincoli di partenza

- Claude Code gira dentro `xterm.js` nel browser: il terminale web non propaga paste di immagini al PTY.
- Claude Code CLI risolve riferimenti `@path/to/file.ext` relativi al `cwd` del terminale.
- Il `cwd` di default del terminale coincide con la project root, quindi path relativi tipo `@project_resources/{project_id}/{stored_name}` sono risolvibili nativamente.
- Esiste già la tabella `project_files` con storage su disco in `project_resources/{project_id}/`.

## Decisioni di design

| Decisione | Scelta | Motivo |
|---|---|---|
| Storage immagini | Riuso tabella `project_files` | Nessuno schema nuovo, stesso flusso di upload |
| Processing immagini | Nessuno (skip `file_reader.extract`) | Non serve FTS su pixel |
| Tag nel terminale | Path relativo `@project_resources/{pid}/{stored_name}` | Risolvibile da Claude Code, stabile, senza collisioni |
| Formato nome | `stored_name` (UUID + estensione) | Unico per costruzione, no collisioni |
| Limite size | 5 MB per file | Compromesso caricamento rapido / immagini utili |
| Formati immagine | png, jpg, jpeg, gif, webp | Coprono i casi comuni |
| UI entry point | Pulsante "Galleria" dentro `TerminalPanel` (fuori xterm.js) | xterm intercetta eventi; il pulsante vive nella toolbar |
| Multi-terminale | Context globale `activeTerminalId` + pulsante per-terminale | Paste Ctrl+V va al terminale focused; click galleria va al terminale di appartenenza |
| Paste Ctrl+V | Ibrido: globale se clipboard contiene immagine + terminale attivo; dentro modale sempre | Rapido ma non ruba paste di testo |
| Contenuto modale | Tutti i file del progetto (anteprima solo per immagini) | Una sola UI per tutto, galleria unificata |

---

## Architettura

### Backend

**`app/services/file_service.py`**
- Estendere `ALLOWED_EXTENSIONS` con `png, jpg, jpeg, gif, webp`.
- Estendere `MIME_MAP` con i MIME corrispondenti (`image/png`, `image/jpeg`, ecc.).
- Nuove costanti:
  - `IMAGE_EXTENSIONS = {"png","jpg","jpeg","gif","webp"}`
  - `MAX_FILE_SIZE = 5 * 1024 * 1024`
- In `upload_files`:
  - Dopo `content = await file.read()`, validare `len(content) <= MAX_FILE_SIZE`; altrimenti `raise ValueError("File exceeds 5 MB limit")`.
  - Se `ext in IMAGE_EXTENSIONS`: saltare `file_reader.extract`, impostare `extraction_status = "skipped"`, `extracted_text = None`, `extracted_at = None`, `file_metadata = None`.

**`app/routers/files.py`**
- Nuovo endpoint `GET /{file_id}/preview`:
  - Ritorna i bytes del file su disco via `FileResponse` con `media_type = record.mime_type` e `filename = record.original_name`.
  - 404 se record o file su disco mancanti.
- L'endpoint esistente `/content` resta invariato (serve solo il testo estratto per file testuali).

**Schemas**
- Nessuna modifica: `ProjectFileResponse` già espone `file_type`, `mime_type`, `stored_name`, `extraction_status`.

**Test backend**
- `tests/test_routers_files.py`:
  - upload PNG valido → 201, record in DB con `extraction_status == "skipped"`
  - upload PNG > 5 MB → 400
  - upload estensione non permessa (es. `.exe`) → 400
  - `GET /{id}/preview` su immagine → 200 con `Content-Type: image/png` e bytes esatti
  - `GET /{id}/preview` su file inesistente → 404

### Frontend

**Context globale**

`src/features/terminals/contexts/active-terminal-context.tsx` (nuovo)
- Provider + hook `useActiveTerminal()`
- State: `{ activeTerminalId: string | null, activeProjectId: string | null }`
- Setter: `setActive(terminalId, projectId)` e `clearActive()`
- Montato nel layout radice dove vivono i terminali (o nel layout di progetto).

**Modifiche `TerminalPanel`**

`src/features/terminals/components/terminal-panel.tsx`
- Nuova prop obbligatoria `projectId: string`.
- Handler `onFocus`/`onClick` sul container del terminale: chiama `setActive(terminalId, projectId)`.
- Nuovo pulsante "Galleria" (icona `Images` di lucide) nella toolbar.
- State locale `galleryOpen: boolean`.
- Click pulsante → apre `<FileGalleryModal open projectId terminalId onSelect onClose>`.
- Ref al WebSocket già esiste (`wsRef`); funzione `injectText(text: string)` interna che fa `wsRef.current?.send(text)`.
- Callback `onSelect(file)` della modale:
  - compone `tag = `@project_resources/${projectId}/${file.stored_name} `` (con trailing space)
  - chiama `injectText(tag)`
  - chiude modale

**Componente galleria**

`src/features/files/components/file-gallery-modal.tsx` (nuovo)
- Props: `{ open: boolean, onClose: () => void, projectId: string, onSelect: (file: ProjectFile) => void }`.
- Usa `Dialog` di shadcn.
- Sezioni:
  1. Header: titolo + toggle filtro "Tutti / Solo immagini" + pulsante chiudi.
  2. Drop zone + pulsante "Carica file" in alto.
  3. Grid scroll verticale con card per ogni file:
     - Se `file_type in IMAGE_EXTENSIONS`: `<img src="/api/projects/{projectId}/files/{id}/preview">` con `object-cover`, aspect-square.
     - Altrimenti: icona generica + nome file + tipo.
     - Click card → `onSelect(file)`.
  4. (Opzionale) badge "Nuovo" per file caricati nella sessione corrente.
- Listener `onPaste` sul contenitore della modale:
  - estrae `clipboardData.items`, filtra `kind === "file"` e `type.startsWith("image/")`.
  - chiama `uploadFiles(projectId, [file])`, refresh lista.
- Upload di più file in parallelo via `Promise.all`; toast di errore se backend rifiuta (size, formato).
- Query di lista via TanStack Query: `useQuery(["project-files", projectId], ...)` con invalidate dopo upload/delete.

**Paste globale**

`src/features/terminals/hooks/use-global-image-paste.ts` (nuovo)
- `useEffect` monta `document.addEventListener("paste", handler)`.
- `handler(e: ClipboardEvent)`:
  - Se `activeTerminalId` e `activeProjectId` sono null → esci.
  - Estrai file immagine dalla clipboard; se nessuno → esci (lascia xterm gestire paste testo).
  - `e.preventDefault()`.
  - Upload dei file all'`activeProjectId`.
  - Per ciascun file caricato: `injectTextToTerminal(activeTerminalId, \`@project_resources/${activeProjectId}/${stored_name} \`)`.
  - Toast informativo: "Immagine caricata e inserita nel terminale".
- Caso `activeTerminalId === null` con immagine in clipboard → toast: "Apri/clicca un terminale prima di incollare".

Per iniettare testo nel terminale attivo serve una mappa `terminalId → WebSocket`. Due opzioni:
- **(a)** Context globale `TerminalRegistryContext` popolato da `TerminalPanel` in mount/unmount con il suo `wsRef`.
- **(b)** Event bus (`window.dispatchEvent(new CustomEvent("terminal:inject", { detail: { terminalId, text } }))`) ascoltato dentro `TerminalPanel`.

Raccomandata **(a)** per tipizzazione e testabilità.

**API client**

`src/features/files/api.ts` (nuovo o estensione di esistente)
- `listFiles(projectId): Promise<ProjectFile[]>`
- `uploadFiles(projectId, files: File[]): Promise<ProjectFile[]>` (multipart)
- `deleteFile(projectId, fileId): Promise<void>`
- `previewUrl(projectId, fileId): string` (solo costruzione URL)

**Tipi**

`src/features/files/types.ts` (nuovo o estensione)
- `ProjectFile` allineato a `ProjectFileResponse` del backend.
- `IMAGE_EXTENSIONS` costante condivisa con component modale per toggle e preview gating.

---

## Flussi utente

### Flusso 1 — Paste rapido di immagine

1. Utente clicca sul terminale A (diventa `activeTerminalId`).
2. Utente preme Ctrl+V con un'immagine in clipboard (screenshot, copia da browser, ecc.).
3. Hook globale intercetta, fa `preventDefault`, carica su `/api/projects/{pid}/files`.
4. Backend salva il file, genera `stored_name = {uuid}.png`, ritorna record.
5. Frontend inserisce `@project_resources/{pid}/{uuid}.png ` nello stdin del terminale A.
6. Claude Code CLI (in esecuzione nel terminale) legge il tag e può aprire il file.

### Flusso 2 — Galleria + selezione

1. Utente clicca pulsante "Galleria" nella toolbar del terminale B.
2. Si apre modale con elenco file del progetto (anteprime per immagini).
3. Utente può caricare nuovi file (upload manuale o drop/paste dentro la modale).
4. Utente clicca su una card.
5. Modale chiude, tag `@project_resources/{pid}/{stored_name} ` inserito nel terminale B.

### Flusso 3 — Multi-terminale edge

- Due terminali aperti, nessuno focused. Utente preme Ctrl+V con immagine → toast "Clicca un terminale prima".
- Terminale A focused, utente apre galleria dal terminale B → selezione va a B (il pulsante galleria è per-terminale, non usa `activeTerminalId`).

---

## Scope fuori

- Nessun tool MCP per servire immagini direttamente a Claude (Claude le legge via path).
- Nessun cleanup automatico delle immagini (gestione manuale tramite endpoint delete esistente).
- Nessun resize / compression lato server.
- Nessuna validazione delle dimensioni pixel.
- Nessuna preview inline dentro il terminale (l'immagine resta riferita solo via path).

---

## Ordine di implementazione

1. **Backend**: `file_service.py` (estensioni + size check) → `files.py` router (`/preview`) → test.
2. **Frontend core**: `ActiveTerminalContext` + `TerminalRegistryContext` + API client + tipi.
3. **Galleria**: `FileGalleryModal` con upload, grid, anteprima, filtro, paste interno.
4. **Integrazione terminale**: pulsante in `TerminalPanel`, prop `projectId`, inject on select.
5. **Paste globale**: `useGlobalImagePaste` montato nel layout di progetto.
6. **Verifica manuale**: upload + paste + multi-terminale + limite 5 MB + Claude risolve `@path`.

---

## Rischi noti

- **Path risolto male da Claude Code**: se il `cwd` del terminale non è la project root, il tag relativo non funziona. Mitigazione: verificare `cwd` in `terminal_service.py`; in fallback usare path assoluto.
- **Paste globale ruba paste testo**: mitigato dal filtro `kind === "file"` + `type.startsWith("image/")`; paste di solo testo non entra nel ramo che chiama `preventDefault`.
- **Registry WebSocket stantio**: se un `TerminalPanel` smonta senza pulire il registry, inject su terminale morto fallisce silenzioso. Mitigazione: cleanup in `useEffect` return + check `readyState === OPEN` prima di `send`.
- **MIME sniffing mancante**: validazione oggi solo su estensione; un utente può rinominare `.exe` in `.png`. Accettabile per strumento interno; non esporre endpoint pubblicamente senza ulteriore validazione.
