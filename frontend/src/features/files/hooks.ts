import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const fileKeys = {
  all: (projectId: string) => ["projects", projectId, "files"] as const,
  formats: ["files", "allowed-formats"] as const,
};

export function useFiles(projectId: string) {
  return useQuery({
    queryKey: fileKeys.all(projectId),
    queryFn: () => api.fetchFiles(projectId),
  });
}

export function useAllowedFormats() {
  return useQuery({
    queryKey: fileKeys.formats,
    queryFn: api.fetchAllowedFormats,
    staleTime: Infinity,
  });
}

export function useUploadFiles(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.uploadFiles(projectId, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteFile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => api.deleteFile(projectId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

