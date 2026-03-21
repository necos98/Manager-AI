import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import IssueList from "../components/IssueList";
import TerminalCommandsEditor from "../components/TerminalCommandsEditor";

const STATUSES = ["All", "New", "Reasoning", "Planned", "Accepted", "Declined", "Finished", "Canceled"];

export default function ProjectDetailPage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [issues, setIssues] = useState([]);
  const [activeTerminalIssueIds, setActiveTerminalIssueIds] = useState([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", path: "", description: "", tech_stack: "" });
  const [editError, setEditError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showMcpSetup, setShowMcpSetup] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [installMsg, setInstallMsg] = useState(null);
  const [installingClaude, setInstallingClaude] = useState(false);
  const [claudeMsg, setClaudeMsg] = useState(null);

  useEffect(() => {
    Promise.all([
      api.getProject(id),
      api.listIssues(id, filter === "All" ? null : filter),
      api.listTerminals(id),
    ]).then(([p, i, terms]) => {
      setProject(p);
      setIssues(i);
      setActiveTerminalIssueIds(terms.map((term) => term.issue_id));
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
              <div className="flex items-center">
                <h1 className="text-2xl font-bold">{project.name}</h1>
                {activeTerminalIssueIds.length > 0 && (
                  <span className="text-sm text-green-600 ml-3">
                    ● {activeTerminalIssueIds.length} terminal{activeTerminalIssueIds.length > 1 ? "s" : ""} active
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    const blob = new Blob(
                      [JSON.stringify({ project_id: project.id }, null, 2)],
                      { type: "application/json" }
                    );
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "manager.json";
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="text-sm text-green-600 hover:text-green-800 px-3 py-1 rounded border border-green-200 hover:bg-green-50"
                >
                  Export manager.json
                </button>
                <button
                  disabled={installing}
                  onClick={async () => {
                    setInstalling(true);
                    setInstallMsg(null);
                    try {
                      const res = await api.installManagerJson(project.id);
                      setInstallMsg({ ok: true, text: `Installed → ${res.path}` });
                    } catch (err) {
                      setInstallMsg({ ok: false, text: err.message });
                    } finally {
                      setInstalling(false);
                    }
                  }}
                  className="text-sm text-teal-600 hover:text-teal-800 px-3 py-1 rounded border border-teal-200 hover:bg-teal-50 disabled:opacity-50"
                >
                  {installing ? "Installing..." : "Install manager.json"}
                </button>
                <button
                  disabled={installingClaude}
                  onClick={async () => {
                    setInstallingClaude(true);
                    setClaudeMsg(null);
                    try {
                      const res = await api.installClaudeResources(project.id);
                      const count = res.copied.length;
                      setClaudeMsg({ ok: true, text: `Installed ${count} item${count !== 1 ? "s" : ""} → ${res.path}` });
                    } catch (err) {
                      setClaudeMsg({ ok: false, text: err.message });
                    } finally {
                      setInstallingClaude(false);
                    }
                  }}
                  className="text-sm text-orange-600 hover:text-orange-800 px-3 py-1 rounded border border-orange-200 hover:bg-orange-50 disabled:opacity-50"
                >
                  {installingClaude ? "Installing..." : "Install Claude Resources"}
                </button>
                <button
                  onClick={() => setShowMcpSetup(true)}
                  className="text-sm text-purple-600 hover:text-purple-800 px-3 py-1 rounded border border-purple-200 hover:bg-purple-50"
                >
                  MCP Setup
                </button>
                <button
                  onClick={startEditing}
                  className="text-sm text-blue-600 hover:text-blue-800 px-3 py-1 rounded border border-blue-200 hover:bg-blue-50"
                >
                  Edit
                </button>
              </div>
            </div>
            {installMsg && (
              <p className={`text-xs mt-1 ${installMsg.ok ? "text-teal-700" : "text-red-600"}`}>
                {installMsg.text}
              </p>
            )}
            {claudeMsg && (
              <p className={`text-xs mt-1 ${claudeMsg.ok ? "text-orange-700" : "text-red-600"}`}>
                {claudeMsg.text}
              </p>
            )}
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
          to={`/projects/${id}/issues/new`}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Issue
        </Link>
      </div>

      <IssueList issues={issues} projectId={id} activeTerminalIssueIds={activeTerminalIssueIds} />

      {/* Terminal Settings */}
      <div className="mt-8 pt-6 border-t">
        <h2 className="text-lg font-bold mb-2">Terminal Settings</h2>
        <p className="text-sm text-gray-500 mb-4">
          These commands run when opening a terminal for this project. When set, they override the global terminal commands.
        </p>
        <TerminalCommandsEditor projectId={id} />
      </div>

      {showMcpSetup && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) setShowMcpSetup(false); }}
        >
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-bold">MCP Server Setup</h2>
              <button
                onClick={() => setShowMcpSetup(false)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                &times;
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <h3 className="font-medium text-sm text-gray-700 mb-1">Endpoint URL</h3>
                <code className="block bg-gray-100 rounded px-3 py-2 text-sm font-mono break-all">
                  http://localhost:8000/mcp/
                </code>
              </div>

              <div>
                <h3 className="font-medium text-sm text-gray-700 mb-2">Claude Code</h3>
                <p className="text-sm text-gray-500 mb-2">
                  Run this command in your terminal:
                </p>
                <pre className="bg-gray-100 rounded px-3 py-2 text-sm font-mono overflow-x-auto whitespace-pre">claude mcp add --transport http ManagerAi http://localhost:8000/mcp/</pre>
              </div>

              <div>
                <h3 className="font-medium text-sm text-gray-700 mb-2">Other MCP Clients</h3>
                <p className="text-sm text-gray-500 mb-2">
                  Add this to your client configuration (Streamable HTTP):
                </p>
                <pre className="bg-gray-100 rounded px-3 py-2 text-sm font-mono overflow-x-auto whitespace-pre">
{JSON.stringify({
  mcpServers: {
    "ManagerAi": {
      type: "url",
      url: "http://localhost:8000/mcp/"
    }
  }
}, null, 2)}
                </pre>
              </div>

              <div>
                <h3 className="font-medium text-sm text-gray-700 mb-1">Project ID</h3>
                <p className="text-sm text-gray-500 mb-2">
                  Most tools require the <code className="bg-gray-100 px-1 rounded">project_id</code> parameter. Use:
                </p>
                <code className="block bg-gray-100 rounded px-3 py-2 text-sm font-mono break-all">
                  {project.id}
                </code>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded p-3">
                <p className="text-sm text-blue-800">
                  <span className="font-medium">Tip:</span> Use the "Export manager.json" button to download a file containing the project ID. Place it in the root of your project so your AI agent can read it automatically.
                </p>
              </div>
            </div>
            <div className="p-4 border-t">
              <button
                onClick={() => setShowMcpSetup(false)}
                className="w-full px-4 py-2 rounded border hover:bg-gray-50 text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
