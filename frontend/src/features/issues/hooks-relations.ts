import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { addRelation, deleteRelation, fetchBlockedIssueIds, fetchRelations } from "./api-relations";
import type { Issue, IssueRelationCreate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export function useRelations(issueId: string) {
  return useQuery({
    queryKey: ["relations", issueId],
    queryFn: () => fetchRelations(issueId),
  });
}

export function useAddRelation(issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueRelationCreate) => addRelation(issueId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relations", issueId] }),
    onError: onMutationError,
  });
}

export function useDeleteRelation(issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (relationId: number) => deleteRelation(issueId, relationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relations", issueId] }),
    onError: onMutationError,
  });
}

export function useBlockedIssueIds(issues: Issue[]) {
  const issueIds = issues.map(i => i.id);
  const { data } = useQuery({
    queryKey: ["relations", "batch", ...issueIds],
    queryFn: () => fetchBlockedIssueIds(issueIds),
    enabled: issueIds.length > 0,
  });
  return new Set(data ?? []);
}
