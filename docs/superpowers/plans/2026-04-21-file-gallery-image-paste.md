# File Gallery & Image Paste Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users upload and paste images into project file storage and reference them as `@path` tags inside the integrated terminal so Claude Code CLI can open them.

**Architecture:** Reuse existing `ProjectFile` table and upload pipeline, extended to accept image extensions and skip text extraction. A new `/preview` endpoint streams raw bytes. Frontend adds a per-terminal gallery modal and a global Ctrl+V image paste hook dispatched to the currently focused terminal via a terminal registry context. Selected files are injected into the terminal WebSocket as `@project_resources/{project_id}/{stored_name} ` path tags that Claude Code resolves natively.

**Tech Stack:** FastAPI, SQLAlchemy async, React 18, Vite, TanStack Query, xterm.js, shadcn/ui, lucide-react.

Reference spec: `docs/fase-7-galleria-immagini.md`.

---

## File Structure

### Backend
- **Modify** `backend/app/services/file_service.py` — extend extension whitelist, add size limit and image skip-extraction branch.
- **Modify** `backend/app/routers/files.py` — add `GET /{file_id}/preview` streaming raw bytes.
- **Modify** `backend/tests/test_routers_files.py` — new test cases (image upload, size limit, preview).

### Frontend
- **Modify** `frontend/src/shared/types/index.ts` — export `IMAGE_EXTENSIONS` constant.
- **Modify** `frontend/src/features/files/api.ts` — add `getFilePreviewUrl`.
- **Create** `frontend/src/features/terminals/contexts/terminal-context.tsx` — provider + hooks `useActiveTerminal`, `useTerminalRegistry`. Holds active terminal id + ws registry.
- **Modify** `frontend/src/features/terminals/components/terminal-panel.tsx` — new `projectId` prop, focus wiring, ws registration, gallery button.
- **Create** `frontend/src/features/files/components/file-gallery-modal.tsx` — modal with grid, upload, paste zone, image/all filter.
- **Create** `frontend/src/features/terminals/hooks/use-global-image-paste.ts` — global paste listener dispatching to active terminal.
- **Modify** `frontend/src/features/terminals/components/terminal-grid.tsx` — pass `projectId`.
- **Modify** `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` — pass `projectId` to `TerminalPanel`.
- **Modify** `frontend/src/routes/projects/$projectId/ask.tsx` — pass `projectId` to `TerminalPanel`.
- **Modify** `frontend/src/App.tsx` (or nearest root layout) — mount `TerminalProvider` and `useGlobalImagePaste`.

---

## Task 1: Backend — extend extensions, size limit, skip extraction for images

**Files:**
- Modify: `backend/app/services/file_service.py:15-25` (constants) and `backend/app/services/file_service.py:39-82` (`upload_files`)
- Test: `backend/tests/test_routers_files.py`

- [ ] **Step 1: Write failing test for image upload**

Append to `backend/tests/test_routers_files.py`:

```python
@pytest.mark.asyncio
async def test_upload_image_skips_extraction(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("photo.png", png_bytes, "image/png"))]
        r = await client.post("/api/projects/p1/files", files=files)
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body) == 1
        assert body[0]["file_type"] == "png"
        assert body[0]["mime_type"] == "image/png"
        assert body[0]["extraction_status"] == "skipped"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    oversized = b"\x00" * (file_service.MAX_FILE_SIZE + 1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("big.png", oversized, "image/png"))]
        r = await client.post("/api/projects/p1/files", files=files)
        assert r.status_code == 400
        assert "5" in r.json()["detail"] or "size" in r.json()["detail"].lower() or "exceed" in r.json()["detail"].lower()

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routers_files.py::test_upload_image_skips_extraction tests/test_routers_files.py::test_upload_rejects_oversized_file -v`
Expected: both FAIL. First fails on `.png not allowed` error, second fails because no size check exists yet (`MAX_FILE_SIZE` attribute may not exist — tests must reference it correctly).

- [ ] **Step 3: Update constants in `file_service.py`**

Replace lines 15-25 of `backend/app/services/file_service.py` with:

```python
ALLOWED_EXTENSIONS = {
    "txt", "md", "doc", "docx", "pdf", "xls", "xlsx",
    "png", "jpg", "jpeg", "gif", "webp",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

MIME_MAP = {
    "txt": "text/plain",
    "md": "text/markdown",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}
```

- [ ] **Step 4: Update `upload_files` to enforce size and skip image extraction**

Replace the body of `upload_files` inside `backend/app/services/file_service.py` (lines 39-82) with:

```python
    async def upload_files(self, project_id: str, files: list[UploadFile]) -> list[ProjectFile]:
        project_dir = os.path.join(BASE_DIR, project_id)
        os.makedirs(project_dir, exist_ok=True)

        results = []
        for file in files:
            ext = _get_extension(file.filename)
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f"File type '.{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

            file_id = str(uuid.uuid4())
            stored_name = f"{file_id}.{ext}"
            file_path = os.path.join(project_dir, stored_name)

            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise ValueError(f"File '{file.filename}' exceeds 5 MB limit")

            with open(file_path, "wb") as f:
                f.write(content)

            mime_type = MIME_MAP.get(ext, "application/octet-stream")

            if ext in IMAGE_EXTENSIONS:
                record = ProjectFile(
                    id=file_id,
                    project_id=project_id,
                    original_name=file.filename,
                    stored_name=stored_name,
                    file_type=ext,
                    file_size=len(content),
                    mime_type=mime_type,
                    file_metadata=None,
                    extracted_text=None,
                    extraction_status="skipped",
                    extraction_error=None,
                    extracted_at=None,
                )
            else:
                result = file_reader.extract(file_path, ext)
                meta: dict[str, Any] = {}
                if result.status == "ok" and file_reader.file_is_low_text(result.text, len(content)):
                    meta["low_text"] = True

                record = ProjectFile(
                    id=file_id,
                    project_id=project_id,
                    original_name=file.filename,
                    stored_name=stored_name,
                    file_type=ext,
                    file_size=len(content),
                    mime_type=mime_type,
                    file_metadata=meta or None,
                    extracted_text=result.text or None,
                    extraction_status=result.status,
                    extraction_error=result.error,
                    extracted_at=datetime.now(timezone.utc) if result.status in ("ok", "failed", "unsupported") else None,
                )

            self.session.add(record)
            results.append(record)

        await self.session.flush()
        return results
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_routers_files.py -v`
Expected: all tests PASS (including pre-existing tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/file_service.py backend/tests/test_routers_files.py
git commit -m "feat(files): accept images and enforce 5 MB size limit"
```

---

## Task 2: Backend — `/preview` endpoint for raw bytes

**Files:**
- Modify: `backend/app/routers/files.py` (append new route after line 71 `delete_file`)
- Test: `backend/tests/test_routers_files.py`

- [ ] **Step 1: Write failing test for preview endpoint**

Append to `backend/tests/test_routers_files.py`:

```python
@pytest.mark.asyncio
async def test_preview_returns_raw_bytes(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(file_service, "BASE_DIR", str(tmp_path))

    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    png_bytes = b"\x89PNG\r\n\x1a\nRAWBYTES"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = [("files", ("pic.png", png_bytes, "image/png"))]
        r = await client.post("/api/projects/p1/files", files=files)
        file_id = r.json()[0]["id"]

        r = await client.get(f"/api/projects/p1/files/{file_id}/preview")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/png")
        assert r.content == png_bytes

        r = await client.get("/api/projects/p1/files/does-not-exist/preview")
        assert r.status_code == 404

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_routers_files.py::test_preview_returns_raw_bytes -v`
Expected: FAIL with 404 on the first GET (endpoint does not exist yet).

- [ ] **Step 3: Add `/preview` route**

Insert into `backend/app/routers/files.py` between the `delete_file` route (ending line 71) and the `get_file_content` route (starting line 74):

```python
@router.get("/{file_id}/preview")
async def preview_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    record = await service.get_by_id(project_id, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = service.get_file_path(project_id, record.stored_name)
    if not __import__("os").path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path=file_path, media_type=record.mime_type, filename=record.original_name)
```

Use a top-of-file `import os` instead of the inline import — replace `if not __import__("os").path.exists(file_path):` with `if not os.path.exists(file_path):` and add `import os` near the existing imports at the top of `files.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_routers_files.py::test_preview_returns_raw_bytes -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/files.py backend/tests/test_routers_files.py
git commit -m "feat(files): add /preview endpoint serving raw bytes"
```

---

## Task 3: Frontend — shared types and API helper

**Files:**
- Modify: `frontend/src/shared/types/index.ts:194-204` (ProjectFile block)
- Modify: `frontend/src/features/files/api.ts`

- [ ] **Step 1: Add `IMAGE_EXTENSIONS` and extend `ProjectFile`**

In `frontend/src/shared/types/index.ts`, replace the `ProjectFile` interface (lines 194-204) with:

```ts
export const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp"] as const;
export type ImageExtension = (typeof IMAGE_EXTENSIONS)[number];

export function isImageExtension(ext: string): ext is ImageExtension {
  return (IMAGE_EXTENSIONS as readonly string[]).includes(ext.toLowerCase());
}

export interface ProjectFile {
  id: string;
  project_id: string;
  original_name: string;
  stored_name: string;
  file_type: string;
  file_size: number;
  mime_type: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  extraction_status?: string | null;
}
```

- [ ] **Step 2: Add preview URL helper**

In `frontend/src/features/files/api.ts`, append after `getFileDownloadUrl`:

```ts
export function getFilePreviewUrl(projectId: string, fileId: string): string {
  return buildUrl(`/projects/${projectId}/files/${fileId}/preview`);
}
```

- [ ] **Step 3: Type-check frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/types/index.ts frontend/src/features/files/api.ts
git commit -m "feat(files): share image-extension helpers and preview URL builder"
```

---

## Task 4: Frontend — terminal context (active terminal + ws registry)

**Files:**
- Create: `frontend/src/features/terminals/contexts/terminal-context.tsx`

- [ ] **Step 1: Create the context module**

Create `frontend/src/features/terminals/contexts/terminal-context.tsx`:

```tsx
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

interface TerminalEntry {
  projectId: string;
  send: (text: string) => boolean;
}

interface TerminalContextValue {
  activeTerminalId: string | null;
  activeProjectId: string | null;
  setActive: (terminalId: string, projectId: string) => void;
  clearActive: (terminalId: string) => void;
  registerTerminal: (terminalId: string, entry: TerminalEntry) => void;
  unregisterTerminal: (terminalId: string) => void;
  injectIntoTerminal: (terminalId: string, text: string) => boolean;
  getProjectIdFor: (terminalId: string) => string | null;
}

const TerminalContext = createContext<TerminalContextValue | null>(null);

export function TerminalProvider({ children }: { children: React.ReactNode }) {
  const [activeTerminalId, setActiveTerminalId] = useState<string | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const registryRef = useRef<Map<string, TerminalEntry>>(new Map());

  const setActive = useCallback((terminalId: string, projectId: string) => {
    setActiveTerminalId(terminalId);
    setActiveProjectId(projectId);
  }, []);

  const clearActive = useCallback((terminalId: string) => {
    setActiveTerminalId((curr) => (curr === terminalId ? null : curr));
    setActiveProjectId((curr) => (activeTerminalId === terminalId ? null : curr));
  }, [activeTerminalId]);

  const registerTerminal = useCallback((terminalId: string, entry: TerminalEntry) => {
    registryRef.current.set(terminalId, entry);
  }, []);

  const unregisterTerminal = useCallback((terminalId: string) => {
    registryRef.current.delete(terminalId);
  }, []);

  const injectIntoTerminal = useCallback((terminalId: string, text: string) => {
    const entry = registryRef.current.get(terminalId);
    if (!entry) return false;
    return entry.send(text);
  }, []);

  const getProjectIdFor = useCallback((terminalId: string) => {
    return registryRef.current.get(terminalId)?.projectId ?? null;
  }, []);

  const value = useMemo<TerminalContextValue>(
    () => ({
      activeTerminalId,
      activeProjectId,
      setActive,
      clearActive,
      registerTerminal,
      unregisterTerminal,
      injectIntoTerminal,
      getProjectIdFor,
    }),
    [activeTerminalId, activeProjectId, setActive, clearActive, registerTerminal, unregisterTerminal, injectIntoTerminal, getProjectIdFor],
  );

  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}

export function useTerminalContext(): TerminalContextValue {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminalContext must be used within TerminalProvider");
  return ctx;
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/terminals/contexts/terminal-context.tsx
git commit -m "feat(terminals): add context for active terminal and ws registry"
```

---

## Task 5: Frontend — `FileGalleryModal` component

**Files:**
- Create: `frontend/src/features/files/components/file-gallery-modal.tsx`

This modal handles listing, upload, paste-to-upload, image/all filter, and card-click selection.

- [ ] **Step 1: Create the modal component**

Create `frontend/src/features/files/components/file-gallery-modal.tsx`:

```tsx
import { useMemo, useRef, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { toast } from "sonner";
import { useFiles, useUploadFiles } from "@/features/files/hooks";
import { getFilePreviewUrl } from "@/features/files/api";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { isImageExtension, type ProjectFile } from "@/shared/types";

interface FileGalleryModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  onSelect: (file: ProjectFile) => void;
}

type Filter = "all" | "images";

export function FileGalleryModal({ open, onClose, projectId, onSelect }: FileGalleryModalProps) {
  const { data: files, isLoading } = useFiles(projectId);
  const uploadFiles = useUploadFiles(projectId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = useMemo(() => {
    if (!files) return [];
    if (filter === "images") return files.filter((f) => isImageExtension(f.file_type));
    return files;
  }, [files, filter]);

  function uploadList(list: FileList | File[]) {
    const formData = new FormData();
    let count = 0;
    for (const f of list) {
      formData.append("files", f);
      count++;
    }
    if (count === 0) return;
    uploadFiles.mutate(formData, {
      onSuccess: () => toast.success(`Uploaded ${count} file(s)`),
    });
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files;
    if (!selected) return;
    uploadList(selected);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handlePaste(e: React.ClipboardEvent<HTMLDivElement>) {
    const items = e.clipboardData?.items;
    if (!items) return;
    const picked: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === "file") {
        const f = item.getAsFile();
        if (f) picked.push(f);
      }
    }
    if (picked.length === 0) return;
    e.preventDefault();
    uploadList(picked);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const dropped = e.dataTransfer?.files;
    if (dropped && dropped.length > 0) uploadList(dropped);
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-4xl" onPaste={handlePaste} onDragOver={(e) => e.preventDefault()} onDrop={handleDrop}>
        <DialogHeader>
          <DialogTitle>Project Files</DialogTitle>
        </DialogHeader>

        <div className="flex items-center gap-3 mb-3">
          <Button disabled={uploadFiles.isPending} asChild>
            <label className="cursor-pointer">
              <Upload className="size-4 mr-2" />
              {uploadFiles.isPending ? "Uploading..." : "Upload"}
              <input
                ref={inputRef}
                type="file"
                multiple
                onChange={handleFileInput}
                disabled={uploadFiles.isPending}
                className="hidden"
              />
            </label>
          </Button>
          <div className="flex items-center gap-1 text-xs">
            <Button
              variant={filter === "all" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilter("all")}
            >
              All
            </Button>
            <Button
              variant={filter === "images" ? "default" : "ghost"}
              size="sm"
              onClick={() => setFilter("images")}
            >
              Images
            </Button>
          </div>
          <span className="text-xs text-muted-foreground ml-auto">
            Paste (Ctrl+V) or drop files here. Click to insert into terminal.
          </span>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-32" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground text-sm">
            No files {filter === "images" ? "(images only)" : ""}.
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3 max-h-[60vh] overflow-y-auto">
            {filtered.map((f) => (
              <button
                key={f.id}
                onClick={() => onSelect(f)}
                className="flex flex-col items-stretch border rounded-md overflow-hidden hover:border-primary text-left"
                title={f.original_name}
              >
                <div className="aspect-square bg-muted flex items-center justify-center overflow-hidden">
                  {isImageExtension(f.file_type) ? (
                    <img
                      src={getFilePreviewUrl(projectId, f.id)}
                      alt={f.original_name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <FileText className="size-10 text-muted-foreground" />
                  )}
                </div>
                <div className="px-2 py-1 text-xs truncate">{f.original_name}</div>
                <div className="px-2 pb-1 text-[10px] uppercase text-muted-foreground">{f.file_type}</div>
              </button>
            ))}
          </div>
        )}

        <div className="flex justify-end mt-3">
          <Button variant="ghost" onClick={onClose}>
            <X className="size-4 mr-1" />
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/files/components/file-gallery-modal.tsx
git commit -m "feat(files): add gallery modal with upload, paste, and selection"
```

---

## Task 6: Frontend — wire `TerminalPanel` with `projectId`, focus, registry, gallery button

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`

- [ ] **Step 1: Update `TerminalPanel` to accept `projectId` and integrate context + gallery**

Replace the entire contents of `frontend/src/features/terminals/components/terminal-panel.tsx` with:

```tsx
import { useCallback, useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { SearchAddon } from "@xterm/addon-search";
import { Copy, Download, Images, Search, X } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { TERMINAL_THEMES } from "@/features/terminals/themes";
import { useSettings } from "@/features/settings/hooks";
import { useTerminalContext } from "@/features/terminals/contexts/terminal-context";
import { FileGalleryModal } from "@/features/files/components/file-gallery-modal";
import type { ProjectFile } from "@/shared/types";
import "xterm/css/xterm.css";

interface TerminalPanelProps {
  terminalId: string;
  projectId: string;
  onSessionEnd?: () => void;
  onDownloadRecording?: () => void;
}

export function TerminalPanel({ terminalId, projectId, onSessionEnd, onDownloadRecording }: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onSessionEndRef = useRef(onSessionEnd);
  const cleanedUpRef = useRef(false);
  const searchAddonRef = useRef<SearchAddon | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "ended">("connecting");
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [galleryOpen, setGalleryOpen] = useState(false);
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 5;

  const { data: settingsList } = useSettings();
  const themeName = settingsList?.find((s) => s.key === "terminal_theme")?.value ?? "catppuccin";
  const termTheme = TERMINAL_THEMES[themeName] ?? TERMINAL_THEMES.catppuccin;

  const { setActive, clearActive, registerTerminal, unregisterTerminal } = useTerminalContext();

  useEffect(() => {
    onSessionEndRef.current = onSessionEnd;
  }, [onSessionEnd]);

  const sendToWs = useCallback((text: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(text);
    return true;
  }, []);

  useEffect(() => {
    registerTerminal(terminalId, { projectId, send: sendToWs });
    return () => {
      unregisterTerminal(terminalId);
    };
  }, [terminalId, projectId, registerTerminal, unregisterTerminal, sendToWs]);

  const handleCopy = useCallback(() => {
    if (!termRef.current) return;
    const selection = termRef.current.getSelection();
    if (selection) {
      navigator.clipboard.writeText(selection).catch(() => {});
    }
  }, []);

  const handleSearch = useCallback((query: string, direction: "next" | "prev" = "next") => {
    if (!searchAddonRef.current || !query) return;
    if (direction === "next") {
      searchAddonRef.current.findNext(query, { incremental: false });
    } else {
      searchAddonRef.current.findPrevious(query);
    }
  }, []);

  const handleFileSelect = useCallback((file: ProjectFile) => {
    const tag = `@project_resources/${projectId}/${file.stored_name} `;
    sendToWs(tag);
    setGalleryOpen(false);
  }, [projectId, sendToWs]);

  const markActive = useCallback(() => {
    setActive(terminalId, projectId);
  }, [setActive, terminalId, projectId]);

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;
    cleanedUpRef.current = false;

    const container = containerRef.current;
    container.innerHTML = "";

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Consolas', monospace",
      theme: termTheme,
    });

    termRef.current = term;

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    const searchAddon = new SearchAddon();
    searchAddonRef.current = searchAddon;
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.loadAddon(searchAddon);

    let opened = false;

    function openIfReady() {
      if (opened || cleanedUpRef.current) return;
      if (container.clientHeight === 0 || container.clientWidth === 0) return;

      opened = true;
      try {
        term.open(container);
        fitAddon.fit();
      } catch {
        return;
      }
      connectWs();
    }

    function connectWs() {
      if (cleanedUpRef.current) return;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/terminals/${terminalId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cleanedUpRef.current) {
          ws.close();
          return;
        }
        setStatus("connected");
        retryCountRef.current = 0;
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        if (!cleanedUpRef.current) term.write(event.data);
      };

      ws.onclose = (event) => {
        if (cleanedUpRef.current) return;
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          onSessionEndRef.current?.();
          return;
        }
        setStatus("disconnected");
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;
          setTimeout(connectWs, delay);
        }
      };

      ws.onerror = () => {};
    }

    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    });

    term.attachCustomKeyEventHandler((e) => {
      if (e.ctrlKey && e.key === "f") {
        e.preventDefault();
        setShowSearch((prev) => !prev);
        return false;
      }
      return true;
    });

    const resizeObserver = new ResizeObserver(() => {
      if (cleanedUpRef.current) return;
      if (!opened) {
        openIfReady();
        return;
      }
      if (container.clientHeight === 0) return;
      try {
        fitAddon.fit();
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      } catch {
        // ignore fit errors during transitions
      }
    });
    resizeObserver.observe(container);

    openIfReady();

    return () => {
      cleanedUpRef.current = true;
      searchAddonRef.current = null;
      termRef.current = null;
      resizeObserver.disconnect();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      clearActive(terminalId);
      const termToDispose = term;
      setTimeout(() => {
        try {
          termToDispose.dispose();
        } catch {}
      }, 50);
    };
  }, [terminalId, clearActive]);

  useEffect(() => {
    if (termRef.current) {
      termRef.current.options.theme = termTheme;
    }
  }, [termTheme]);

  return (
    <div
      className="flex flex-col h-full"
      style={{ background: termTheme.background }}
      onMouseDownCapture={markActive}
      onFocusCapture={markActive}
    >
      <div className="flex items-center justify-end gap-1 px-2 py-1 bg-zinc-900 border-b border-zinc-800">
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
          onClick={() => setGalleryOpen(true)}
          title="Open file gallery"
          aria-label="Open file gallery"
        >
          <Images className="size-3 mr-1" />
          Files
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
          onClick={handleCopy}
          title="Copy selection"
          aria-label="Copy terminal selection"
        >
          <Copy className="size-3 mr-1" />
          Copy
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
          onClick={() => setShowSearch((p) => !p)}
          title="Search (Ctrl+F)"
          aria-label="Search in terminal"
        >
          <Search className="size-3" />
        </Button>
        {onDownloadRecording && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
            onClick={onDownloadRecording}
            title="Download session recording"
            aria-label="Download session recording"
          >
            <Download className="size-3 mr-1" />
            Log
          </Button>
        )}
      </div>
      {status === "ended" && (
        <div className="px-3 py-2 bg-zinc-800 text-zinc-400 text-sm text-center">
          Terminal session ended
        </div>
      )}
      {status === "disconnected" && (
        <div className="px-3 py-2 bg-yellow-900 text-yellow-300 text-sm text-center">
          Reconnecting...
        </div>
      )}
      {showSearch && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 border-b border-zinc-700">
          <Search className="size-3.5 text-zinc-400 flex-shrink-0" />
          <Input
            autoFocus
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              handleSearch(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch(searchQuery, e.shiftKey ? "prev" : "next");
              if (e.key === "Escape") setShowSearch(false);
            }}
            placeholder="Search… (Enter next, Shift+Enter prev)"
            className="h-6 text-xs bg-zinc-900 border-zinc-600 text-zinc-200 flex-1"
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 text-zinc-400"
            onClick={() => setShowSearch(false)}
            aria-label="Close search"
          >
            <X className="size-3" />
          </Button>
        </div>
      )}
      <div ref={containerRef} className="flex-1 min-h-0" />
      <FileGalleryModal
        open={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        projectId={projectId}
        onSelect={handleFileSelect}
      />
    </div>
  );
}
```

- [ ] **Step 2: Type-check (expect errors at call sites due to missing `projectId` prop)**

Run: `cd frontend && npx tsc --noEmit`
Expected: errors complaining that `projectId` is missing at existing `<TerminalPanel>` usages in `terminal-grid.tsx`, `issues/$issueId.tsx`, and `ask.tsx`. Leave these for the next task.

- [ ] **Step 3: Commit (defer type-check clean until Task 7)**

```bash
git add frontend/src/features/terminals/components/terminal-panel.tsx
git commit -m "feat(terminals): add gallery button, ws registry, and active-terminal wiring"
```

---

## Task 7: Frontend — update `TerminalPanel` call sites with `projectId`

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-grid.tsx:64`
- Modify: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx:132,142,152`
- Modify: `frontend/src/routes/projects/$projectId/ask.tsx:75`

- [ ] **Step 1: Update `terminal-grid.tsx`**

In `frontend/src/features/terminals/components/terminal-grid.tsx`, replace line 64:

```tsx
<TerminalPanel terminalId={term.id} projectId={term.project_id} />
```

- [ ] **Step 2: Update issue page**

In `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`, add `projectId={projectId}` to all three `<TerminalPanel ...>` usages around lines 132, 142, 152. The component already has `projectId` in scope (from the route params). If unsure, locate the route hook near the top and confirm, e.g.:

```tsx
const { projectId } = Route.useParams();
```

Then each usage becomes:

```tsx
<TerminalPanel
  terminalId={terminal1.id}
  projectId={projectId}
  onSessionEnd={() => killTerminal.mutate(terminal1.id)}
  onDownloadRecording={() => handleDownload(terminal1.id)}
/>
```

(Apply the same change to the `terminal2.id` instance.)

- [ ] **Step 3: Update ask page**

In `frontend/src/routes/projects/$projectId/ask.tsx` around line 75, add `projectId={projectId}` to the `<TerminalPanel>`. The route params give you `projectId`; confirm via `Route.useParams()` at the top of the file.

```tsx
<TerminalPanel
  terminalId={terminalId}
  projectId={projectId}
  onSessionEnd={handleNewConversation}
/>
```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/terminals/components/terminal-grid.tsx frontend/src/routes/projects/\$projectId/issues/\$issueId.tsx frontend/src/routes/projects/\$projectId/ask.tsx
git commit -m "feat(terminals): pass projectId to TerminalPanel call sites"
```

---

## Task 8: Frontend — global image paste hook

**Files:**
- Create: `frontend/src/features/terminals/hooks/use-global-image-paste.ts`

- [ ] **Step 1: Create the hook**

Create `frontend/src/features/terminals/hooks/use-global-image-paste.ts`:

```ts
import { useEffect } from "react";
import { toast } from "sonner";
import { uploadFiles as uploadFilesApi } from "@/features/files/api";
import { useTerminalContext } from "@/features/terminals/contexts/terminal-context";
import { useQueryClient } from "@tanstack/react-query";
import { fileKeys } from "@/features/files/hooks";

export function useGlobalImagePaste() {
  const { activeTerminalId, activeProjectId, injectIntoTerminal } = useTerminalContext();
  const queryClient = useQueryClient();

  useEffect(() => {
    function extractImageFiles(cd: DataTransfer | null): File[] {
      if (!cd) return [];
      const out: File[] = [];
      for (let i = 0; i < cd.items.length; i++) {
        const item = cd.items[i];
        if (item.kind === "file" && item.type.startsWith("image/")) {
          const f = item.getAsFile();
          if (f) out.push(f);
        }
      }
      return out;
    }

    async function handler(e: ClipboardEvent) {
      const images = extractImageFiles(e.clipboardData);
      if (images.length === 0) return;

      if (!activeTerminalId || !activeProjectId) {
        toast.error("Click a terminal before pasting an image");
        return;
      }

      e.preventDefault();
      const projectId = activeProjectId;
      const terminalId = activeTerminalId;

      try {
        const formData = new FormData();
        for (const img of images) {
          const ext = (img.type.split("/")[1] ?? "png").toLowerCase();
          const name = img.name && img.name.includes(".") ? img.name : `pasted.${ext}`;
          formData.append("files", img, name);
        }
        const records = await uploadFilesApi(projectId, formData);
        queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
        for (const rec of records) {
          const tag = `@project_resources/${projectId}/${rec.stored_name} `;
          injectIntoTerminal(terminalId, tag);
        }
        toast.success(`Pasted ${records.length} image(s) into terminal`);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Image upload failed");
      }
    }

    document.addEventListener("paste", handler);
    return () => document.removeEventListener("paste", handler);
  }, [activeTerminalId, activeProjectId, injectIntoTerminal, queryClient]);
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/terminals/hooks/use-global-image-paste.ts
git commit -m "feat(terminals): global Ctrl+V image paste to active terminal"
```

---

## Task 9: Frontend — mount provider and global paste in root layout

**Files:**
- Modify: `frontend/src/App.tsx` (or the nearest wrapper around `RouterProvider` / app tree)

- [ ] **Step 1: Locate the root component**

Run: `cd frontend && cat src/App.tsx || cat src/main.tsx`
Identify where providers (QueryClientProvider, etc.) are set up. Use that file for the next step.

- [ ] **Step 2: Wrap tree with `TerminalProvider` and invoke `useGlobalImagePaste`**

In the root component file, import:

```tsx
import { TerminalProvider } from "@/features/terminals/contexts/terminal-context";
import { useGlobalImagePaste } from "@/features/terminals/hooks/use-global-image-paste";
```

Create a small inner component to use the hook (hooks cannot run outside the provider):

```tsx
function GlobalPasteBridge() {
  useGlobalImagePaste();
  return null;
}
```

Wrap the existing app tree:

```tsx
<TerminalProvider>
  <GlobalPasteBridge />
  {/* ...existing providers and RouterProvider... */}
</TerminalProvider>
```

`TerminalProvider` must sit **inside** `QueryClientProvider` (since `useGlobalImagePaste` uses `useQueryClient`).

- [ ] **Step 3: Type-check and run dev server**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

Then: `cd frontend && npm run dev` (start server, leave running for manual verification in Task 10).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(app): mount TerminalProvider and global image paste bridge"
```

---

## Task 10: Manual end-to-end verification

No code changes. Validate the full feature in a browser.

- [ ] **Step 1: Start the full stack**

Run from repo root: `python start.py`
Expected: backend on 8000, frontend on dev port. Wait for "Application startup complete".

- [ ] **Step 2: Scenario A — upload via gallery button**

1. Open a project in the UI and navigate to a terminal.
2. Click the **Files** button in the terminal toolbar.
3. Upload a PNG via the Upload button.
4. Confirm the card shows a thumbnail preview.
5. Click the card.
6. Confirm the terminal receives `@project_resources/{project_id}/{stored_name} ` as input (visible in the shell prompt or passed to Claude).

- [ ] **Step 3: Scenario B — Ctrl+V paste into focused terminal**

1. With two terminals open in split view, click terminal A to focus.
2. Copy a screenshot to clipboard (Win+Shift+S).
3. Press Ctrl+V anywhere in the app (not inside an `<input>`).
4. Confirm toast "Pasted 1 image(s) into terminal".
5. Confirm terminal A received the `@path` tag.

- [ ] **Step 4: Scenario C — paste without focused terminal**

1. Refresh the page, don't click any terminal.
2. Copy an image, press Ctrl+V.
3. Confirm toast "Click a terminal before pasting an image".
4. Confirm no upload occurred (gallery remains unchanged after opening it).

- [ ] **Step 5: Scenario D — size limit**

1. Pick an image > 5 MB.
2. Upload via gallery.
3. Confirm backend returns 400 and UI shows an error toast.

- [ ] **Step 6: Scenario E — paste of plain text still reaches xterm**

1. Copy plain text.
2. Focus xterm inside a terminal.
3. Ctrl+V.
4. Confirm the text is written to the terminal normally (hook should not `preventDefault` for non-image clipboard content).

- [ ] **Step 7: Commit (docs only — no code)**

If any issues surfaced in verification, return to the relevant task to fix before proceeding. If all pass, this task is complete (no commit needed).

---

## Self-Review Notes

- **Spec coverage:** upload images (Task 1), preview endpoint (Task 2), gallery UI with tabs & preview (Task 5), per-terminal gallery button + inject (Task 6), multi-terminal `activeTerminalId` routing (Tasks 4, 8), global paste ibrido (Task 8), size limit 5 MB (Task 1), tag format `@project_resources/{pid}/{stored_name}` (Tasks 6, 8). Rischi from spec ("cwd non project root", "registry stantio") addressed via `readyState` check in `sendToWs` and cleanup in Task 6 unmount.
- **Type consistency:** `ProjectFile` shape used uniformly (stored_name, file_type); hook name `useTerminalContext` and context value `injectIntoTerminal` match between Tasks 4, 6, 8; `fileKeys` import in Task 8 matches the export in `hooks.ts` observed during research.
- **No placeholders:** all code blocks contain complete, runnable code; no "implement error handling" prose.
