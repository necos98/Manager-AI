import { StatusBadge } from "./status-badge";
import type { Task } from "@/shared/types";

interface TaskListProps {
  tasks: Task[];
}

export function TaskList({ tasks }: TaskListProps) {
  if (tasks.length === 0) return null;

  return (
    <div className="space-y-1">
      {tasks.map((task) => (
        <div key={task.id} className="flex items-center gap-2 text-sm">
          <StatusBadge status={task.status} />
          <span>{task.name}</span>
        </div>
      ))}
    </div>
  );
}
