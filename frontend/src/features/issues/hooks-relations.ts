import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { addRelation, deleteRelation, fetchRelations } from "./api-relations";
import type { Issue, IssueRelationCreate } from "@/shared/types";

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
  });
}

export function useDeleteRelation(issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (relationId: number) => deleteRelation(issueId, relationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["relations", issueId] }),
  });
}

export function useBlockedIssueIds(issues: Issue[]) {
  const results = useQueries({
    queries: issues.map((i) => ({
      queryKey: ["relations", i.id],
      queryFn: () => fetchRelations(i.id),
    })),
  });
  const blockedIds = new Set<string>();
  results.forEach((result, idx) => {
    (result.data ?? []).forEach((r) => {
      if (r.relation_type === "blocks" && r.target_id === issues[idx].id) {
        blockedIds.add(r.target_id);
      }
    });
  });
  return blockedIds;
}
