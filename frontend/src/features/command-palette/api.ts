import { apiGet } from "@/shared/api/client";
import type { SearchResults } from "@/shared/types";

export function searchAll(query: string): Promise<SearchResults> {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  const qs = params.toString();
  return apiGet<SearchResults>(`/search${qs ? `?${qs}` : ""}`);
}
