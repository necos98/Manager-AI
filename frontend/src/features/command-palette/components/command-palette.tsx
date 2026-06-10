import { useEffect, useRef, useCallback, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Search, ArrowUp, ArrowDown, Command, FileText, FolderOpen, Globe } from "lucide-react";
import { Dialog, DialogContent, DialogOverlay } from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { cn } from "@/shared/lib/utils";
import { useCommandPalette, type CategoryMap } from "../hooks";
import type { SearchResultItem } from "@/shared/types";

const CATEGORY_LABELS: Record<keyof CategoryMap, string> = {
  issues: "Issues",
  projects: "Projects",
  pages: "Pages",
};

const CATEGORY_ICONS: Record<keyof CategoryMap, React.ReactNode> = {
  issues: <FileText className="h-4 w-4" />,
  projects: <FolderOpen className="h-4 w-4" />,
  pages: <Globe className="h-4 w-4" />,
};

function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="bg-yellow-200 dark:bg-yellow-700 rounded-sm px-0.5">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const {
    query,
    setQuery,
    selectedIndex,
    categoryOrder,
    data,
    isLoading,
    flatResults,
    hasResults,
    closePalette,
    selectNext,
    selectPrev,
    getSelectedItem,
  } = useCommandPalette();

  // Sync external open state
  useEffect(() => {
    if (open) {
      // Small delay for the dialog animation before autofocus
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const handleSelect = useCallback(
    (item: SearchResultItem) => {
      closePalette();
      onOpenChange(false);
      navigate({ to: item.url as any });
    },
    [closePalette, navigate, onOpenChange],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        selectNext();
        break;
      case "ArrowUp":
        e.preventDefault();
        selectPrev();
        break;
      case "Enter":
        e.preventDefault();
        const selected = getSelectedItem();
        if (selected) {
          handleSelect(selected.item);
        }
        break;
      case "Escape":
        e.preventDefault();
        closePalette();
        onOpenChange(false);
        break;
      case "Tab":
        e.preventDefault();
        // Tab cycles through categories
        break;
    }
  };

  // Scroll selected item into view
  useEffect(() => {
    if (!resultsRef.current) return;
    const el = resultsRef.current.querySelector("[data-selected='true']");
    if (el) {
      el.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  // Build category → items map for grouped rendering
  const groupedResults = categoryOrder.reduce(
    (acc, cat) => {
      const items = (data?.[cat] ?? []) as SearchResultItem[];
      if (items.length > 0) {
        acc[cat] = items;
      }
      return acc;
    },
    {} as Record<string, SearchResultItem[]>,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogOverlay className="bg-black/40 backdrop-blur-sm" />
      <DialogContent
        data-command-palette=""
        className="top-[15vh] translate-y-0 max-w-2xl p-0 gap-0 overflow-hidden"
        onKeyDown={handleKeyDown}
        showCloseButton={false}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="h-5 w-5 text-muted-foreground shrink-0" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search issues, projects, pages..."
            className="border-0 shadow-none focus-visible:ring-0 px-0 h-8 text-base"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            <Command className="h-3 w-3" />
            K
          </kbd>
        </div>

        {/* Loading indicator */}
        {isLoading && query.trim().length >= 1 && (
          <div className="px-4 py-3 text-sm text-muted-foreground">Searching...</div>
        )}

        {/* No results */}
        {!isLoading && query.trim().length >= 1 && !hasResults && (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No results found for <strong>"{query}"</strong>
          </div>
        )}

        {/* Results */}
        {hasResults && (
          <div
            ref={resultsRef}
            className="max-h-[60vh] overflow-y-auto py-2"
          >
            {categoryOrder.map((cat) => {
              const items = groupedResults[cat];
              if (!items || items.length === 0) return null;
              let globalIndex = 0;
              // Calculate starting index for this category
              for (const prevCat of categoryOrder) {
                if (prevCat === cat) break;
                globalIndex += (data?.[prevCat] ?? []).length;
              }

              return (
                <div key={cat} className="mb-1">
                  <div className="flex items-center gap-2 px-4 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    {CATEGORY_ICONS[cat]}
                    {CATEGORY_LABELS[cat]}
                  </div>
                  {items.map((item, idx) => {
                    const absoluteIdx = globalIndex + idx;
                    const isSelected = absoluteIdx === selectedIndex;

                    return (
                      <div
                        key={`${cat}-${item.id}`}
                        data-selected={isSelected ? "true" : undefined}
                        className={cn(
                          "flex items-center gap-3 px-4 py-2.5 cursor-pointer text-sm transition-colors",
                          isSelected
                            ? "bg-accent text-accent-foreground"
                            : "hover:bg-muted/50",
                        )}
                        onClick={() => handleSelect(item)}
                        onMouseEnter={() => {
                          // Update selected index on hover
                          useCommandPalette.getState?.();
                        }}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium truncate">
                              {highlightMatch(item.name, query)}
                            </span>
                            {item.status && (
                              <span className="shrink-0 text-xs text-muted-foreground capitalize">
                                {item.status.toLowerCase()}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground truncate mt-0.5">
                            {highlightMatch(item.description || item.url, query)}
                          </div>
                        </div>
                        {item.project_name && (
                          <span className="shrink-0 text-xs text-muted-foreground">
                            {item.project_name}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}

        {/* Footer hint */}
        {hasResults && (
          <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <ArrowUp className="h-3 w-3" />
              <ArrowDown className="h-3 w-3" />
              Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">Enter</kbd>
              Select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">Esc</kbd>
              Close
            </span>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && query.trim().length === 0 && (
          <div className="px-4 py-8 text-center">
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground mb-4">
              <Command className="h-4 w-4" />
              <span>Start typing to search across all projects</span>
            </div>
            <div className="text-xs text-muted-foreground space-y-1">
              <p>
                <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">g</kbd>{" "}
                <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">i</kbd> Issues
                &middot;{" "}
                <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">g</kbd>{" "}
                <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">d</kbd> Dashboard
                &middot;{" "}
                <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">n</kbd> New Issue
                &middot;{" "}
                <kbd className="rounded border bg-muted px-1 py-0 text-[10px]">?</kbd> Help
              </p>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
