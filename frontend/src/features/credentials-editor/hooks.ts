import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const envKeys = {
  all: ["credentials-env"] as const,
};

export const presetKeys = {
  all: ["credentials-presets"] as const,
};

export function useCredentialsEnv() {
  return useQuery({
    queryKey: envKeys.all,
    queryFn: api.fetchEnv,
  });
}

export function useUpdateEnv() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: Record<string, string>) => api.updateEnv(variables),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: envKeys.all });
    },
    onError: onMutationError,
  });
}

export function usePresets() {
  return useQuery({
    queryKey: presetKeys.all,
    queryFn: api.fetchPresets,
  });
}

export function useCreatePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: api.PresetCreate) => api.createPreset(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: presetKeys.all });
    },
    onError: onMutationError,
  });
}

export function useUpdatePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: api.PresetUpdate }) => api.updatePreset(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: presetKeys.all });
    },
    onError: onMutationError,
  });
}

export function useDeletePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deletePreset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: presetKeys.all });
    },
    onError: onMutationError,
  });
}

export function useApplyPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.applyPreset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: envKeys.all });
    },
    onError: onMutationError,
  });
}
