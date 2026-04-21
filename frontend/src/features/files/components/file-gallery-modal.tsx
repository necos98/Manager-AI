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
      if (item && item.kind === "file") {
        const f = item.getAsFile();
        if (f) picked.push(f);
      }
    }
    if (picked.length === 0) return;
    e.preventDefault();
    e.stopPropagation();
    e.nativeEvent.stopImmediatePropagation();
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
