import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Terminal } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { Badge } from "@/shared/components/ui/badge";
import { Card } from "@/shared/components/ui/card";
import { StatusBadge } from "./status-badge";
import type { Issue } from "@/shared/types";

interface KanbanCardProps {
  issue: Issue;
  hasTerminal: boolean;
  isBlocked?: boolean;
  projectId: string;
  activePipelineName?: string;
  selectMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: (issueId: string) => void;
}

function TaskProgress({ tasks }: { tasks: Issue["tasks"] }) {
  if (!tasks || tasks.length === 0) return null;
  const completed = tasks.filter((t) => t.status === "Completed").length;
  const total = tasks.length;
  const percent = Math.round((completed / total) * 100);
  return (
    <div className="flex items-center gap-2 mt-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${percent}%` }} />
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">{completed}/{total}</span>
    </div>
  );
}

export function KanbanCard({ issue, hasTerminal, isBlocked = false, projectId, activePipelineName, selectMode = false, isSelected = false, onToggleSelect }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: issue.id,
    data: { issue },
    disabled: selectMode, // disable drag when in select mode
  });
  const navigate = useNavigate();

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.4 : 1,
  };

  function handleClick(e: React.MouseEvent) {
    if (isDragging) return;
    if (selectMode) {
      onToggleSelect?.(issue.id);
      return;
    }
    navigate({ to: "/projects/$projectId/issues/$issueId", params: { projectId, issueId: issue.id } });
  }

  function handleCheckboxClick(e: React.MouseEvent) {
    e.stopPropagation();
    onToggleSelect?.(issue.id);
  }

  const label = `Issue ${issue.name || issue.description}, status ${issue.status}, priority ${issue.priority}`;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="touch-none"
      role="article"
      aria-label={label}
      aria-grabbed={isDragging}
      aria-selected={selectMode ? isSelected : undefined}
    >
      <Card
        onClick={handleClick}
        className={[
          "px-3 py-2.5 cursor-pointer transition-colors",
          isSelected
            ? "ring-2 ring-primary bg-primary/5 hover:bg-primary/10"
            : "hover:bg-accent/50",
        ].join(" ")}
      >
        <div className="flex items-start gap-2">
          {selectMode && (
            <Checkbox
              checked={isSelected}
              onClick={handleCheckboxClick}
              className="mt-1 flex-shrink-0"
              aria-label={`Select ${issue.name || issue.description}`}
            />
          )}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              {hasTerminal && (
                <Terminal className="size-3 text-green-500 dark:text-green-400 flex-shrink-0 drop-shadow-[0_0_4px_rgba(74,222,128,0.5)]" />
              )}
              {isBlocked && (
                <span className="text-xs bg-destructive/15 text-destructive px-1.5 py-0.5 rounded font-medium flex-shrink-0">
                  Blocked
                </span>
              )}
              {issue.category && (
                <Badge variant="secondary" className="text-[10px] px-1 py-0 leading-snug">{issue.category}</Badge>
              )}
              {activePipelineName && (
                <span className="flex items-center gap-1 text-[10px] text-blue-600">
                  <span className="size-1.5 rounded-full bg-blue-500" />
                  <span className="max-w-20 truncate">{activePipelineName}</span>
                </span>
              )}
            </div>
            <p className="text-sm font-medium truncate mt-0.5">
              {issue.name || issue.description}
            </p>
            {issue.name && (
              <p className="text-xs text-muted-foreground truncate">{issue.description}</p>
            )}
          </div>
          <span className="text-xs text-muted-foreground flex-shrink-0">P{issue.priority}</span>
        </div>
        <TaskProgress tasks={issue.tasks} />
      </Card>
    </div>
  );
}
