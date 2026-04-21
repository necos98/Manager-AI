import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Terminal } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { Card } from "@/shared/components/ui/card";
import { StatusBadge } from "./status-badge";
import type { Issue } from "@/shared/types";

interface KanbanCardProps {
  issue: Issue;
  hasTerminal: boolean;
  isBlocked?: boolean;
  projectId: string;
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

export function KanbanCard({ issue, hasTerminal, isBlocked = false, projectId }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: issue.id,
    data: { issue },
  });
  const navigate = useNavigate();

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.4 : 1,
  };

  function handleClick() {
    if (!isDragging) {
      navigate({ to: "/projects/$projectId/issues/$issueId", params: { projectId, issueId: issue.id } });
    }
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
    >
      <Card onClick={handleClick} className="px-3 py-2.5 cursor-pointer hover:bg-accent/50 transition-colors">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              {hasTerminal && (
                <Terminal className="size-3 text-green-500 flex-shrink-0" style={{ filter: "drop-shadow(0 0 4px #4ade80)" }} />
              )}
              {isBlocked && (
                <span className="text-xs bg-destructive/15 text-destructive px-1.5 py-0.5 rounded font-medium flex-shrink-0">
                  Blocked
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
