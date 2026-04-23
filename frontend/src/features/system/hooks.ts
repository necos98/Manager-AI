import { useQuery } from "@tanstack/react-query";
import * as api from "./api";

export const systemKeys = {
  info: ["system", "info"] as const,
};

export function useSystemInfo() {
  return useQuery({
    queryKey: systemKeys.info,
    queryFn: () => api.fetchSystemInfo(),
    staleTime: 5 * 60 * 1000,
  });
}
