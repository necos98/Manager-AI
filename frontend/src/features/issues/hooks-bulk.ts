import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as bulkApi from "./api-bulk";
import { issueKeys } from "./hooks";
import type {
  BulkStatusUpdate,
  BulkTagsUpdate,
  BulkDeleteRequest,
  BulkPriorityUpdate,
  BulkCategoryUpdate,
} from "./api-bulk";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Bulk operation failed");
};

export function useBulkUpdateStatus(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkStatusUpdate) => bulkApi.bulkUpdateStatus(projectId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: issueKeys.all(projectId) });
      if (res.errors && Object.keys(res.errors).length > 0) {
        toast.warning(`Updated ${res.updated} issues. ${Object.keys(res.errors).length} error(s).`);
      } else {
        toast.success(`Updated ${res.updated} issue(s)`);
      }
    },
    onError: onMutationError,
  });
}

export function useBulkUpdateTags(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkTagsUpdate) => bulkApi.bulkUpdateTags(projectId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: issueKeys.all(projectId) });
      if (res.errors && Object.keys(res.errors).length > 0) {
        toast.warning(`Updated ${res.updated} issues. ${Object.keys(res.errors).length} error(s).`);
      } else {
        toast.success(`Tags updated on ${res.updated} issue(s)`);
      }
    },
    onError: onMutationError,
  });
}

export function useBulkDelete(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkDeleteRequest) => bulkApi.bulkDeleteIssues(projectId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: issueKeys.all(projectId) });
      if (res.errors && Object.keys(res.errors).length > 0) {
        toast.warning(`Deleted ${res.deleted} issues. ${Object.keys(res.errors).length} error(s).`);
      } else {
        toast.success(`Deleted ${res.deleted} issue(s)`);
      }
    },
    onError: onMutationError,
  });
}

export function useBulkUpdatePriority(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkPriorityUpdate) => bulkApi.bulkUpdatePriority(projectId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: issueKeys.all(projectId) });
      if (res.errors && Object.keys(res.errors).length > 0) {
        toast.warning(`Updated ${res.updated} issues. ${Object.keys(res.errors).length} error(s).`);
      } else {
        toast.success(`Priority updated on ${res.updated} issue(s)`);
      }
    },
    onError: onMutationError,
  });
}

export function useBulkUpdateCategory(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkCategoryUpdate) => bulkApi.bulkUpdateCategory(projectId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: issueKeys.all(projectId) });
      if (res.errors && Object.keys(res.errors).length > 0) {
        toast.warning(`Updated ${res.updated} issues. ${Object.keys(res.errors).length} error(s).`);
      } else {
        toast.success(`Category updated on ${res.updated} issue(s)`);
      }
    },
    onError: onMutationError,
  });
}
