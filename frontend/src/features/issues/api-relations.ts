import { request } from "@/shared/api/client";
import type { IssueRelation, IssueRelationCreate } from "@/shared/types";

export function fetchRelations(issueId: string): Promise<IssueRelation[]> {
  return request(`/issues/${issueId}/relations`);
}

export function addRelation(issueId: string, data: IssueRelationCreate): Promise<IssueRelation> {
  return request(`/issues/${issueId}/relations`, { method: "POST", body: JSON.stringify(data) });
}

export function deleteRelation(issueId: string, relationId: number): Promise<null> {
  return request(`/issues/${issueId}/relations/${relationId}`, { method: "DELETE" });
}
