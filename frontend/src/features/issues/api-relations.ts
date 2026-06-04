import { apiGet, apiPost, apiDelete } from "@/shared/api/client";
import type { IssueRelation, IssueRelationCreate } from "@/shared/types";

export function fetchRelations(issueId: string): Promise<IssueRelation[]> {
  return apiGet<IssueRelation[]>(`/issues/${issueId}/relations`);
}

export function addRelation(issueId: string, data: IssueRelationCreate): Promise<IssueRelation> {
  return apiPost<IssueRelation>(`/issues/${issueId}/relations`, data);
}

export function deleteRelation(issueId: string, relationId: number): Promise<null> {
  return apiDelete(`/issues/${issueId}/relations/${relationId}`);
}

export function fetchBlockedIssueIds(issueIds: string[]): Promise<string[]> {
  return apiPost<{ blocked_ids: string[] }>("/issues/relations/batch", { issue_ids: issueIds })
    .then(r => r.blocked_ids);
}
