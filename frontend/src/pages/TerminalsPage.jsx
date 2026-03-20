import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function TerminalsPage() {
  const [terminals, setTerminals] = useState([]);
  const [softLimit, setSoftLimit] = useState(5);
  const [loading, setLoading] = useState(true);

  const fetchTerminals = () => {
    api.listTerminals().then(setTerminals).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTerminals();
    api.terminalConfig().then((cfg) => setSoftLimit(cfg.soft_limit)).catch(() => {});
    const interval = setInterval(fetchTerminals, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleKill = async (terminalId) => {
    if (!confirm("Kill this terminal? Any running commands will be terminated.")) return;
    try {
      await api.killTerminal(terminalId);
      setTerminals((prev) => prev.filter((t) => t.id !== terminalId));
    } catch (err) {
      alert("Failed to kill terminal: " + err.message);
    }
  };

  const formatAge = (createdAt) => {
    const diff = Date.now() - new Date(createdAt).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m ago`;
  };

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Active Terminals</h1>
        <span className="text-sm text-gray-500">{terminals.length} / {softLimit} (soft limit)</span>
      </div>

      {terminals.length === 0 ? (
        <p className="text-gray-500">No active terminals.</p>
      ) : (
        <div className="space-y-3">
          {terminals.map((term) => (
            <div key={term.id} className="flex items-center bg-white rounded-lg border p-4">
              <span
                className="w-2.5 h-2.5 rounded-full bg-green-400 mr-4 flex-shrink-0"
                style={{ boxShadow: "0 0 6px #4ade80" }}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900">{term.task_name || term.task_id}</p>
                <p className="text-sm text-gray-500">
                  <span className="text-blue-600">{term.project_name || term.project_id}</span>
                  {" · "}Started {formatAge(term.created_at)}
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                <Link
                  to={`/projects/${term.project_id}/tasks/${term.task_id}`}
                  className="text-sm text-blue-600 border border-blue-200 px-3 py-1.5 rounded hover:bg-blue-50"
                >
                  Go to Task
                </Link>
                <button
                  onClick={() => handleKill(term.id)}
                  className="text-sm text-red-600 border border-red-200 px-3 py-1.5 rounded hover:bg-red-50"
                >
                  Kill
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
