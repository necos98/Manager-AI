import { apiPost } from "@/shared/api/client";
import type { ImportResult } from "@/shared/types";

export function importEntities(fileContent: string, scope: string = "both"): Promise<ImportResult> {
  return apiPost<ImportResult>("/import", { file_content: fileContent, scope });
}

export function resolveImport(overwriteIds: string[], fileContent: string, scope: string = "both"): Promise<ImportResult> {
  return apiPost<ImportResult>("/import/resolve", {
    overwrite_ids: overwriteIds,
    file_content: fileContent,
    scope,
  });
}
