import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { IssueCompleteBody, IssueCreate, IssueFeedbackCreate, IssueStatus, IssueStatusUpdate, IssueUpdate, TaskCreate, TaskUpdate } from "@/shared/types";

export const issueKeys = {
  all: (projectId: string) => ["projects", projectId, "issues"] as const,
  detail: (projectId: string, issueId: string) => ["projects", projectId, "issues", issueId] as const,
  tasks: (projectId: string, issueId: string) => ["projects", projectId, "issues", issueId, "tasks"] as const,
};

export function useIssues(projectId: string, status?: IssueStatus, search?: string) {
  return useQuery({
    queryKey: ["issues", projectId, status, search],
    queryFn: () => api.fetchIssues(projectId, status, search),
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

export function useUpdateIssueStatus(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ issueId, status }: { issueId: string; status: IssueStatus }) =>
      api.updateIssueStatus(projectId, issueId, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["issues", projectId] });
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

export const feedbackKeys = {
  all: (projectId: string, issueId: string) =>
    ["projects", projectId, "issues", issueId, "feedback"] as const,
};

export function useStartAnalysis(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.startAnalysis(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useAcceptIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.acceptIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useCancelIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.cancelIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useCompleteIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueCompleteBody) => api.completeIssue(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useFeedback(projectId: string, issueId: string) {
  return useQuery({
    queryKey: feedbackKeys.all(projectId, issueId),
    queryFn: () => api.fetchFeedback(projectId, issueId),
  });
}

export function useAddFeedback(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueFeedbackCreate) => api.addFeedback(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: feedbackKeys.all(projectId, issueId) });
    },
  });
}

export function useUpdateTask(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: TaskUpdate }) =>
      api.updateTask(projectId, issueId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useDeleteTask(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => api.deleteTask(projectId, issueId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useCreateTasks(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tasks: TaskCreate[]) => api.createTasks(projectId, issueId, tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}

export function useReplaceTasks(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tasks: TaskCreate[]) => api.replaceTasks(projectId, issueId, tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
    },
  });
}
