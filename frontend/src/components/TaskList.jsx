import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function TaskList({ tasks, projectId }) {
  if (tasks.length === 0) return <p className="text-gray-500">No tasks yet.</p>;

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <Link
          key={task.id}
          to={`/projects/${projectId}/tasks/${task.id}`}
          className="flex items-center justify-between bg-white rounded border p-3 hover:shadow-sm transition-shadow"
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">{task.name || task.description}</p>
            {task.name && <p className="text-sm text-gray-500 truncate">{task.description}</p>}
          </div>
          <div className="flex items-center gap-3 ml-4">
            <span className="text-sm text-gray-400">P{task.priority}</span>
            <StatusBadge status={task.status} />
          </div>
        </Link>
      ))}
    </div>
  );
}
