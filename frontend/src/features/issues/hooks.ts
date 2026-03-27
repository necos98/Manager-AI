import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { IssueCreate, IssueStatus, IssueStatusUpdate, IssueUpdate } from "@/shared/types";

export const issueKeys = {
  all: (projectId: string) => ["projects", projectId, "issues"] as const,
  detail: (projectId: string, issueId: string) => ["projects", projectId, "issues", issueId] as const,
  tasks: (projectId: string, issueId: string) => ["projects", projectId, "issues", issueId, "tasks"] as const,
};

export function useIssues(projectId: string, status?: IssueStatus) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), status] as const,
    queryFn: () => api.fetchIssues(projectId, status),
  });
}

export function useIssue(projectId: string, issueId: string) {
  return useQuery({
    queryKey: issueKeys.detail(projectId, issueId),
    queryFn: () => api.fetchIssue(projectId, issueId),
  });
}

export function useCreateIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueCreate) => api.createIssue(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useUpdateIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueUpdate) => api.updateIssue(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useUpdateIssueStatus(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueStatusUpdate) => api.updateIssueStatus(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useDeleteIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (issueId: string) => api.deleteIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}
