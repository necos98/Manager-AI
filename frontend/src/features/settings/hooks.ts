import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const settingKeys = {
  all: ["settings"] as const,
};

export function useSettings() {
  return useQuery({
    queryKey: settingKeys.all,
    queryFn: api.fetchSettings,
  });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => api.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
    onError: onMutationError,
  });
}

export function useResetSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => api.resetSetting(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
    onError: onMutationError,
  });
}

export function useResetAllSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.resetAllSettings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
    onError: onMutationError,
  });
}
