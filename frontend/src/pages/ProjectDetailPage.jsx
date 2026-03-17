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
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", path: "", description: "", tech_stack: "" });
  const [editError, setEditError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getProject(id),
      api.listTasks(id, filter === "All" ? null : filter),
    ]).then(([p, t]) => {
      setProject(p);
      setTasks(t);
    }).finally(() => setLoading(false));
  }, [id, filter]);

  const startEditing = () => {
    setEditForm({ name: project.name, path: project.path, description: project.description || "", tech_stack: project.tech_stack || "" });
    setEditError(null);
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setEditError(null);
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setEditError(null);
    try {
      const updated = await api.updateProject(id, editForm);
      setProject(updated);
      setEditing(false);
    } catch (err) {
      setEditError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p>Loading...</p>;
  if (!project) return <p>Project not found.</p>;

  return (
    <div>
      <div className="mb-6">
        {editing ? (
          <form onSubmit={saveEdit} className="space-y-3 max-w-lg">
            {editError && <p className="text-red-600 text-sm">{editError}</p>}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                required
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Path</label>
              <input
                type="text"
                required
                value={editForm.path}
                onChange={(e) => setEditForm({ ...editForm, path: e.target.value })}
                className="w-full border rounded px-3 py-2 font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                className="w-full border rounded px-3 py-2"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tech Stack</label>
              <textarea
                value={editForm.tech_stack}
                onChange={(e) => setEditForm({ ...editForm, tech_stack: e.target.value })}
                className="w-full border rounded px-3 py-2"
                rows={3}
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={cancelEditing}
                className="px-4 py-2 rounded border hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="flex items-start justify-between">
              <h1 className="text-2xl font-bold">{project.name}</h1>
              <button
                onClick={startEditing}
                className="text-sm text-blue-600 hover:text-blue-800 px-3 py-1 rounded border border-blue-200 hover:bg-blue-50"
              >
                Edit
              </button>
            </div>
            <p className="text-sm text-gray-500 font-mono">{project.path}</p>
            {project.description && <p className="text-gray-600 mt-2">{project.description}</p>}
            {project.tech_stack && (
              <p className="text-sm text-gray-500 mt-1">
                <span className="font-medium">Tech Stack:</span> {project.tech_stack}
              </p>
            )}
            <p className="text-xs text-gray-400 mt-1 font-mono">ID: {project.id}</p>
          </>
        )}
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
