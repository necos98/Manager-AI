import { useState, useMemo } from "react";
import { DndContext, DragEndEvent, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { KanbanColumn } from "./kanban-column";
import { KanbanCard } from "./kanban-card";
import { KanbanFilters, SortKey } from "./kanban-filters";
import { useUpdateIssueStatus } from "@/features/issues/hooks";
import type { Issue, IssueStatus } from "@/shared/types";

const COLUMNS: IssueStatus[] = ["New", "Reasoning", "Planned", "Accepted", "Finished", "Canceled"];

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
}

export function KanbanBoard({ issues, projectId, activeTerminalIssueIds, blockedIssueIds = new Set() }: KanbanBoardProps) {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("all");
  const [sort, setSort] = useState<SortKey>("priority");
  const [pending, setPending] = useState<PendingTransition | null>(null);
  const [activeIssue, setActiveIssue] = useState<Issue | null>(null);
  const updateStatus = useUpdateIssueStatus(projectId);

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
    filtered.forEach((i) => map.get(i.status)?.push(i));
    return map;
  }, [filtered]);

  function handleDragStart(event: { active: { id: string; data: { current?: { issue: Issue } } } }) {
    setActiveIssue(event.active.data.current?.issue ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveIssue(null);
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

  return (
    <>
      <KanbanFilters
        search={search}
        onSearchChange={setSearch}
        priority={priority}
        onPriorityChange={setPriority}
        sort={sort}
        onSortChange={setSort}
      />

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart as any} onDragEnd={handleDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-4">
          {COLUMNS.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              issues={byStatus.get(status) ?? []}
              activeTerminalIssueIds={activeTerminalIssueIds}
              blockedIssueIds={blockedIssueIds}
              isValidTarget={activeIssue ? isValidTransition(activeIssue.status, status) : false}
            />
          ))}
        </div>
        <DragOverlay>
          {activeIssue && (
            <KanbanCard
              issue={activeIssue}
              hasTerminal={activeTerminalIssueIds.includes(activeIssue.id)}
              isBlocked={blockedIssueIds.has(activeIssue.id)}
            />
          )}
        </DragOverlay>
      </DndContext>

      <Dialog open={!!pending} onOpenChange={(open) => !open && setPending(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambia stato</DialogTitle>
            <DialogDescription>
              Sposta "{pending?.issue.name || pending?.issue.description}" da {pending?.issue.status} a {pending?.to}?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>Annulla</Button>
            <Button onClick={confirmTransition} disabled={updateStatus.isPending}>
              {updateStatus.isPending ? "..." : "Conferma"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
