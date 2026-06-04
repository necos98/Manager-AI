import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as importApi from "./api";
import { agentKeys } from "@/features/agents/hooks";
import { pipelineKeys } from "@/features/pipelines/hooks";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export function useImportEntities() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fileContent, scope }: { fileContent: string; scope?: string }) =>
      importApi.importEntities(fileContent, scope),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useResolveImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      overwriteIds,
      fileContent,
      scope,
    }: {
      overwriteIds: string[];
      fileContent: string;
      scope?: string;
    }) => importApi.resolveImport(overwriteIds, fileContent, scope),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}
