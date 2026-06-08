import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const providerKeys = {
  list: ["agent-providers"] as const,
  details: ["provider-details"] as const,
  default: ["agent-provider-setting"] as const,
};

export function useAgentProviderList() {
  return useQuery({
    queryKey: providerKeys.list,
    queryFn: api.fetchAgentProviders,
  });
}

export function useProviderDetails() {
  return useQuery({
    queryKey: providerKeys.details,
    queryFn: api.fetchProviderDetails,
  });
}

export function useDefaultProvider() {
  return useQuery({
    queryKey: providerKeys.default,
    queryFn: api.fetchAgentProviderSetting,
  });
}

export function useUpdateDefaultProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => api.updateAgentProviderSetting(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: providerKeys.default });
      toast.success("Default provider updated");
    },
    onError: onMutationError,
  });
}
