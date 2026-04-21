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
        if (item && item.kind === "file" && item.type.startsWith("image/")) {
          const f = item.getAsFile();
          if (f) out.push(f);
        }
      }
      return out;
    }

    async function handler(e: ClipboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target && target.closest('[role="dialog"]')) return;
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
