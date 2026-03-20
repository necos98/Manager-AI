import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function TaskList({ tasks, projectId, activeTerminalTaskIds = [] }) {
  if (tasks.length === 0) return <p className="text-gray-500">No tasks yet.</p>;

  return (
    <div className="space-y-2">
      {tasks.map((task) => {
        const hasTerminal = activeTerminalTaskIds.includes(task.id);
        return (
          <Link
            key={task.id}
            to={`/projects/${projectId}/tasks/${task.id}`}
            className="flex items-center justify-between bg-white rounded border p-3 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-center flex-1 min-w-0">
              {hasTerminal && (
                <span
                  className="w-2 h-2 rounded-full bg-green-400 mr-3 flex-shrink-0"
                  style={{ boxShadow: "0 0 6px #4ade80" }}
                  title="Terminal active"
                />
              )}
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">{task.name || task.description}</p>
                {task.name && <p className="text-sm text-gray-500 truncate">{task.description}</p>}
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              {hasTerminal && (
                <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">terminal</span>
              )}
              <span className="text-sm text-gray-400">P{task.priority}</span>
              <StatusBadge status={task.status} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
