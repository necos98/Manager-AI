import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";

export default function NewTaskPage() {
  const { id: projectId } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({ description: "", priority: 3 });
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.createTask(projectId, form);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">New Task</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            required
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border rounded px-3 py-2"
            rows={4}
            placeholder="Describe what needs to be done..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority (1 = highest, 5 = lowest)</label>
          <select
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
            className="w-full border rounded px-3 py-2"
          >
            {[1, 2, 3, 4, 5].map((p) => (
              <option key={p} value={p}>
                {p} {p === 1 ? "(Highest)" : p === 5 ? "(Lowest)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-3">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Create
          </button>
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}`)}
            className="px-4 py-2 rounded border hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
