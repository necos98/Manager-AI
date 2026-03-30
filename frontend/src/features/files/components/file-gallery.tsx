import { useRef } from "react";
import { Download, Trash2, Upload } from "lucide-react";
import { useFiles, useAllowedFormats, useUploadFiles, useDeleteFile } from "@/features/files/hooks";
import { getFileDownloadUrl } from "@/features/files/api";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

interface FileGalleryProps {
  projectId: string;
}

export function FileGallery({ projectId }: FileGalleryProps) {
  const { data: files, isLoading } = useFiles(projectId);
  const { data: formats } = useAllowedFormats();
  const uploadFiles = useUploadFiles(projectId);
  const deleteFile = useDeleteFile(projectId);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected || selected.length === 0) return;

    const formData = new FormData();
    for (const file of selected) {
      formData.append("files", file);
    }

    uploadFiles.mutate(formData, {
      onSettled: () => {
        if (inputRef.current) inputRef.current.value = "";
      },
    });
  };

  const handleDelete = (fileId: string, fileName: string) => {
    if (!window.confirm(`Delete "${fileName}"?`)) return;
    deleteFile.mutate(fileId);
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <Button disabled={uploadFiles.isPending} asChild>
          <label className="cursor-pointer">
            <Upload className="size-4 mr-2" />
            {uploadFiles.isPending ? "Uploading..." : "Upload Files"}
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={formats?.accept || ""}
              onChange={handleUpload}
              disabled={uploadFiles.isPending}
              className="hidden"
            />
          </label>
        </Button>
        {formats?.label && (
          <span className="text-xs text-muted-foreground">{formats.label}</span>
        )}
      </div>

      {uploadFiles.error && (
        <p className="text-sm text-destructive mb-3">{uploadFiles.error.message}</p>
      )}

      {!files || files.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No files uploaded.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">Size</th>
              <th className="py-2 pr-4 font-medium">Uploaded</th>
              <th className="py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id} className="border-b hover:bg-accent">
                <td className="py-2 pr-4 font-medium truncate max-w-xs" title={f.original_name}>
                  {f.original_name}
                </td>
                <td className="py-2 pr-4 text-muted-foreground uppercase">{f.file_type}</td>
                <td className="py-2 pr-4 text-muted-foreground">{formatSize(f.file_size)}</td>
                <td className="py-2 pr-4 text-muted-foreground">{formatDate(f.created_at)}</td>
                <td className="py-2 flex gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <a href={getFileDownloadUrl(projectId, f.id)} download>
                      <Download className="size-3 mr-1" />
                      Download
                    </a>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleDelete(f.id, f.original_name)}
                  >
                    <Trash2 className="size-3 mr-1" />
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
