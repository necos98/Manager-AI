import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { ProjectCreate, ProjectUpdate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const projectKeys = {
  all: ["projects"] as const,
  list: (archived: boolean) => ["projects", "list", { archived }] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects(archived: boolean = false) {
  return useQuery({
    queryKey: projectKeys.list(archived),
    queryFn: () => api.fetchProjects(archived),
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => api.fetchProject(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) => api.createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: onMutationError,
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectUpdate) => api.updateProject(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: onMutationError,
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: onMutationError,
  });
}

export function useInstallManagerJson(projectId: string) {
  return useMutation({
    mutationFn: () => api.installManagerJson(projectId),
    onError: onMutationError,
  });
}

export function useInstallClaudeResources(projectId: string) {
  return useMutation({
    mutationFn: () => api.installClaudeResources(projectId),
    onError: onMutationError,
  });
}

export function useCodebaseIndexStatus(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "codebase-index-status"] as const,
    queryFn: () => api.fetchCodebaseIndexStatus(projectId),
    enabled: !!projectId,
  });
}

export function useTriggerCodebaseIndex(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.triggerCodebaseIndex(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "codebase-index-status"] });
    },
    onError: onMutationError,
  });
}

export function useArchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.archiveProject(projectId),
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: onMutationError,
  });
}

export function useUnarchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.unarchiveProject(projectId),
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: onMutationError,
  });
}
