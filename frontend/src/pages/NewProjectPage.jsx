import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function NewProjectPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", path: "", description: "" });
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const project = await api.createProject(form);
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">New Project</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Path</label>
          <input
            type="text"
            required
            value={form.path}
            onChange={(e) => setForm({ ...form, path: e.target.value })}
            className="w-full border rounded px-3 py-2 font-mono"
            placeholder="/home/user/my-project"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full border rounded px-3 py-2"
            rows={4}
            placeholder="Describe the project context..."
          />
        </div>
        <div className="flex gap-3">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Create
          </button>
          <button type="button" onClick={() => navigate("/")} className="px-4 py-2 rounded border hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
