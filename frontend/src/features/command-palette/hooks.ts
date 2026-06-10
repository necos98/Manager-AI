import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchAll } from "./api";
import type { SearchResultItem } from "@/shared/types";

/**
 * Debounced global search hook for the command palette.
 * Skips the query when the text is too short.
 */
export function useGlobalSearch(query: string) {
  return useQuery({
    queryKey: ["global-search", query],
    queryFn: () => searchAll(query),
    enabled: query.trim().length >= 1,
    staleTime: 30_000, // 30s cache
  });
}

export interface CommandPaletteState {
  open: boolean;
  query: string;
  selectedIndex: number;
  categoryOrder: Array<keyof CategoryMap>;
}

export interface CategoryMap {
  issues: SearchResultItem[];
  projects: SearchResultItem[];
  pages: SearchResultItem[];
}

export function useCommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [categoryOrder, setCategoryOrder] = useState<Array<keyof CategoryMap>>([
    "issues",
    "projects",
    "pages",
  ]);

  const { data, isLoading } = useGlobalSearch(query);

  // Build flat list for keyboard navigation
  const buildFlatResults = (): { item: SearchResultItem; category: keyof CategoryMap }[] => {
    if (!data) return [];
    const flat: { item: SearchResultItem; category: keyof CategoryMap }[] = [];
    for (const cat of categoryOrder) {
      for (const item of data[cat] ?? []) {
        flat.push({ item, category: cat });
      }
    }
    return flat;
  };

  const flatResults = buildFlatResults();
  const hasResults = flatResults.length > 0;

  const openPalette = () => {
    setOpen(true);
    setQuery("");
    setSelectedIndex(0);
  };

  const closePalette = () => {
    setOpen(false);
    setQuery("");
    setSelectedIndex(0);
  };

  const selectNext = () => {
    if (flatResults.length === 0) return;
    setSelectedIndex((prev) => Math.min(prev + 1, flatResults.length - 1));
  };

  const selectPrev = () => {
    if (flatResults.length === 0) return;
    setSelectedIndex((prev) => Math.max(prev - 1, 0));
  };

  const getSelectedItem = () => {
    return flatResults[selectedIndex] ?? null;
  };

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  return {
    open,
    setOpen,
    query,
    setQuery,
    selectedIndex,
    setSelectedIndex,
    categoryOrder,
    data,
    isLoading,
    flatResults,
    hasResults,
    openPalette,
    closePalette,
    selectNext,
    selectPrev,
    getSelectedItem,
  };
}
