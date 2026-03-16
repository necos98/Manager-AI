import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import TaskList from "../components/TaskList";

const STATUSES = ["All", "New", "Planned", "Accepted", "Declined", "Finished", "Canceled"];

export default function ProjectDetailPage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getProject(id),
      api.listTasks(id, filter === "All" ? null : filter),
    ]).then(([p, t]) => {
      setProject(p);
      setTasks(t);
    }).finally(() => setLoading(false));
  }, [id, filter]);

  if (loading) return <p>Loading...</p>;
  if (!project) return <p>Project not found.</p>;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{project.name}</h1>
        <p className="text-sm text-gray-500 font-mono">{project.path}</p>
        {project.description && <p className="text-gray-600 mt-2">{project.description}</p>}
        <p className="text-xs text-gray-400 mt-1 font-mono">ID: {project.id}</p>
      </div>

      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-2">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1 rounded text-sm ${
                filter === s ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <Link
          to={`/projects/${id}/tasks/new`}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Task
        </Link>
      </div>

      <TaskList tasks={tasks} projectId={id} />
    </div>
  );
}
