import { useCallback, useMemo, useState } from "react";
import { DndContext, DragStartEvent, DragEndEvent, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { KanbanColumn } from "./kanban-column";
import { KanbanCard } from "./kanban-card";
import { KanbanFilters, SortKey } from "./kanban-filters";
import { BulkActionBar } from "./bulk-action-bar";
import { useUpdateIssueStatus, useIssues, issueKeys } from "@/features/issues/hooks";
import { useQueryClient } from "@tanstack/react-query";
import type { Issue, IssueStatus } from "@/shared/types";
import { ListChecks, X } from "lucide-react";

const COLUMNS: IssueStatus[] = ["New", "Reasoning", "Planned", "Accepted", "Finished", "Canceled"];

const FINISHED_PAGE_SIZE = 10;

const VALID_TRANSITIONS = new Set([
  "New->Reasoning",
  "Reasoning->Planned",
  "Planned->Accepted",
  "Accepted->Finished",
]);

function isValidTransition(from: IssueStatus, to: IssueStatus): boolean {
  return VALID_TRANSITIONS.has(`${from}->${to}`) || to === "Canceled";
}

interface PendingTransition {
  issue: Issue;
  to: IssueStatus;
}

interface KanbanBoardProps {
  issues: Issue[];
  projectId: string;
  activeTerminalIssueIds: string[];
  blockedIssueIds?: Set<string>;
  tag: string;
  onTagChange: (tag: string) => void;
  availableTags: string[];
  activeRunsByIssue?: Record<string, { pipeline_name: string; status: string } | null>;
}

export function KanbanBoard({ issues, projectId, activeTerminalIssueIds, blockedIssueIds = new Set(), tag, onTagChange, availableTags, activeRunsByIssue }: KanbanBoardProps) {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("all");
  const [sort, setSort] = useState<SortKey>("priority");
  const [pending, setPending] = useState<PendingTransition | null>(null);
  const [activeIssue, setActiveIssue] = useState<Issue | null>(null);
  const [finishedOffset, setFinishedOffset] = useState(0);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIssueIds, setSelectedIssueIds] = useState<Set<string>>(new Set());
  const updateStatus = useUpdateIssueStatus(projectId);
  const queryClient = useQueryClient();

  const resolvedTag = tag !== "all" ? tag : undefined;

  const { data: finishedPage, isFetching: finishedLoading } = useIssues(
    projectId, "Finished", undefined, resolvedTag, FINISHED_PAGE_SIZE, finishedOffset
  );

  // Derive allFinished from React Query cache instead of duplicating state via useEffect.
  const allFinished = useMemo(() => {
    const result: Issue[] = [];
    const numPages = Math.floor(finishedOffset / FINISHED_PAGE_SIZE) + 1;
    for (let i = 0; i < numPages; i++) {
      const offset = i * FINISHED_PAGE_SIZE;
      const key = [...issueKeys.all(projectId), "list", {
        status: "Finished" as IssueStatus,
        search: undefined,
        tag: resolvedTag,
        limit: FINISHED_PAGE_SIZE,
        offset,
      }];
      const page = queryClient.getQueryData<Issue[]>(key);
      if (page) result.push(...page);
    }
    return result;
  }, [finishedOffset, finishedPage, resolvedTag, projectId, queryClient]);

  // Reset pagination when tag filter changes
  const [prevTag, setPrevTag] = useState(tag);
  if (tag !== prevTag) {
    setFinishedOffset(0);
    setPrevTag(tag);
  }

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const filtered = useMemo(() => {
    let list = issues;
    if (search) {
      const term = search.toLowerCase();
      list = list.filter((i) => i.description.toLowerCase().includes(term) || i.name?.toLowerCase().includes(term));
    }
    if (priority !== "all") {
      list = list.filter((i) => String(i.priority) === priority);
    }
    return [...list].sort((a, b) => {
      if (sort === "priority") return a.priority - b.priority;
      if (sort === "created_at") return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [issues, search, priority, sort]);

  const byStatus = useMemo(() => {
    const map = new Map<IssueStatus, Issue[]>();
    COLUMNS.forEach((s) => map.set(s, []));
    filtered.filter(i => i.status !== "Finished").forEach((i) => map.get(i.status)?.push(i));
    map.set("Finished", allFinished);
    return map;
  }, [filtered, allFinished]);

  const handleToggleSelect = useCallback((issueId: string) => {
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      if (next.has(issueId)) {
        next.delete(issueId);
      } else {
        next.add(issueId);
      }
      return next;
    });
  }, []);

  const handleSelectAllInColumn = useCallback((status: IssueStatus) => {
    const colIssues = byStatus.get(status) ?? [];
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      for (const i of colIssues) next.add(i.id);
      return next;
    });
  }, [byStatus]);

  const handleDeselectAllInColumn = useCallback((status: IssueStatus) => {
    const colIssues = byStatus.get(status) ?? [];
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      for (const i of colIssues) next.delete(i.id);
      return next;
    });
  }, [byStatus]);

  const handleClearSelection = useCallback(() => {
    setSelectedIssueIds(new Set());
    setSelectMode(false);
  }, []);

  function handleDragStart(event: DragStartEvent) {
    if (selectMode) return;
    setActiveIssue(event.active.data.current?.issue ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveIssue(null);
    if (selectMode) return;
    const { active, over } = event;
    if (!over) return;
    const issue = issues.find((i) => i.id === active.id);
    const newStatus = over.id as IssueStatus;
    if (!issue || issue.status === newStatus) return;
    if (!isValidTransition(issue.status, newStatus)) return;
    setPending({ issue, to: newStatus });
  }

  async function confirmTransition() {
    if (!pending) return;
    await updateStatus.mutateAsync({ issueId: pending.issue.id, status: pending.to });
    setPending(null);
  }

  const allIssues = useMemo(() => {
    const result: Issue[] = [];
    for (const [, colIssues] of byStatus) {
      result.push(...colIssues);
    }
    return result;
  }, [byStatus]);

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <KanbanFilters
          search={search}
          onSearchChange={setSearch}
          priority={priority}
          onPriorityChange={setPriority}
          sort={sort}
          onSortChange={setSort}
          tag={tag}
          onTagChange={onTagChange}
          availableTags={availableTags}
        />
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          {selectMode ? (
            <>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {selectedIssueIds.size} selected
              </span>
              <Button variant="ghost" size="sm" onClick={handleClearSelection}>
                <X className="size-3.5 mr-1" />
                Cancel
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectMode(true)}
            >
              <ListChecks className="size-3.5 mr-1" />
              Select
            </Button>
          )}
        </div>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-4">
          {COLUMNS.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              issues={byStatus.get(status) ?? []}
              activeTerminalIssueIds={activeTerminalIssueIds}
              blockedIssueIds={blockedIssueIds}
              isValidTarget={selectMode ? false : activeIssue ? isValidTransition(activeIssue.status, status) : false}
              projectId={projectId}
              activeRunsByIssue={activeRunsByIssue}
              selectMode={selectMode}
              selectedIssueIds={selectedIssueIds}
              onToggleSelect={handleToggleSelect}
              onSelectAll={() => handleSelectAllInColumn(status)}
              onDeselectAll={() => handleDeselectAllInColumn(status)}
              {...(status === "Finished" ? {
                onLoadMore: () => setFinishedOffset(prev => prev + FINISHED_PAGE_SIZE),
                hasMore: finishedPage != null && finishedPage.length >= FINISHED_PAGE_SIZE,
                isLoadingMore: finishedLoading,
              } : {})}
            />
          ))}
        </div>
        <DragOverlay>
          {activeIssue && !selectMode && (
            <KanbanCard
              issue={activeIssue}
              hasTerminal={activeTerminalIssueIds.includes(activeIssue.id)}
              isBlocked={blockedIssueIds.has(activeIssue.id)}
              activePipelineName={activeRunsByIssue?.[activeIssue.id]?.pipeline_name}
            />
          )}
        </DragOverlay>
      </DndContext>

      {selectMode && selectedIssueIds.size > 0 && (
        <BulkActionBar
          projectId={projectId}
          selectedIssueIds={selectedIssueIds}
          allIssues={allIssues}
          onComplete={handleClearSelection}
        />
      )}

      <Dialog open={!!pending} onOpenChange={(open) => !open && setPending(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change status</DialogTitle>
            <DialogDescription>
              Move &quot;{pending?.issue.name || pending?.issue.description}&quot; from {pending?.issue.status} to {pending?.to}?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>Cancel</Button>
            <Button onClick={confirmTransition} disabled={updateStatus.isPending}>
              {updateStatus.isPending ? "..." : "Conferma"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
