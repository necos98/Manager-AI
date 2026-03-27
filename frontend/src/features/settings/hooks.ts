import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

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
  });
}

export function useResetSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => api.resetSetting(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
  });
}

export function useResetAllSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.resetAllSettings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
  });
}
