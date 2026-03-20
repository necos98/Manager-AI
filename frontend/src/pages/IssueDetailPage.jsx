import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import MarkdownViewer from "../components/MarkdownViewer";
import StatusBadge from "../components/StatusBadge";
import TerminalPanel from "../components/TerminalPanel";

export default function IssueDetailPage() {
  const { id: projectId, issueId } = useParams();
  const navigate = useNavigate();
  const [issue, setIssue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [terminalId, setTerminalId] = useState(null);
  const [terminalLoading, setTerminalLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("details");
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [showLimitWarning, setShowLimitWarning] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getIssue(projectId, issueId),
      api.listTerminals(null, issueId),
    ]).then(([i, terminals]) => {
      setIssue(i);
      if (terminals.length > 0) {
        setTerminalId(terminals[0].id);
      }
    }).finally(() => setLoading(false));
  }, [projectId, issueId]);

  const openTerminal = async () => {
    const [{ count }, { soft_limit }] = await Promise.all([
      api.terminalCount(),
      api.terminalConfig(),
    ]);
    if (count >= soft_limit) {
      setShowLimitWarning(true);
      return;
    }
    await doOpenTerminal();
  };

  const doOpenTerminal = async () => {
    setShowLimitWarning(false);
    setTerminalLoading(true);
    try {
      const term = await api.createTerminal(issueId, projectId);
      setTerminalId(term.id);
      setActiveTab("terminal");
    } catch (err) {
      alert("Failed to open terminal: " + err.message);
    } finally {
      setTerminalLoading(false);
    }
  };

  const closeTerminal = async () => {
    setShowCloseConfirm(false);
    if (terminalId) {
      try {
        await api.killTerminal(terminalId);
      } catch {
        // Terminal may already be dead
      }
      setTerminalId(null);
      setActiveTab("details");
    }
  };

  if (loading) return <p>Loading...</p>;
  if (!issue) return <p>Issue not found.</p>;

  const tabs = [
    { id: "details", label: "Details" },
  ];
  if (terminalId) {
    tabs.push({ id: "terminal", label: "Terminal" });
  }

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 100px)" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to issues
        </button>
        {terminalId ? (
          <button
            onClick={() => setShowCloseConfirm(true)}
            className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 flex items-center gap-2 text-sm"
          >
            <span className="font-mono">&#9632;</span> Close Terminal
          </button>
        ) : (
          <button
            onClick={openTerminal}
            disabled={terminalLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 text-sm"
          >
            <span className="font-mono">&#9654;</span> {terminalLoading ? "Opening..." : "Open Terminal"}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b mb-0 flex-shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {tab.label}
            {tab.id === "terminal" && (
              <span className="ml-2 w-2 h-2 rounded-full bg-green-400 inline-block" style={{ boxShadow: "0 0 6px #4ade80" }} />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0">
        {/* Details tab */}
        <div
          className={`bg-white rounded-b-lg shadow-sm border border-t-0 overflow-y-auto ${activeTab === "details" ? "block h-full" : "hidden"}`}
        >
          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h1 className="text-2xl font-bold">{issue.name || "Untitled Issue"}</h1>
                <p className="text-sm text-gray-500 mt-1">Priority: {issue.priority}</p>
              </div>
              <StatusBadge status={issue.status} />
            </div>

            <div className="mb-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Description</h2>
              <p className="text-gray-700 text-sm">{issue.description}</p>
            </div>

            {issue.specification && (
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Specification</h2>
                <div className="bg-indigo-50 rounded p-3">
                  <MarkdownViewer content={issue.specification} />
                </div>
              </div>
            )}

            {issue.plan && (
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Plan</h2>
                <div className="bg-gray-50 rounded p-3">
                  <MarkdownViewer content={issue.plan} />
                </div>
              </div>
            )}

            {issue.tasks && issue.tasks.length > 0 && (
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Tasks</h2>
                <div className="space-y-1">
                  {issue.tasks.map((task) => (
                    <div key={task.id} className="flex items-center gap-2 text-sm">
                      <StatusBadge status={task.status} />
                      <span className="text-gray-700">{task.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {issue.recap && (
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Recap</h2>
                <div className="bg-green-50 rounded p-3">
                  <MarkdownViewer content={issue.recap} />
                </div>
              </div>
            )}

            {issue.decline_feedback && (
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Decline Feedback</h2>
                <p className="text-red-700 bg-red-50 rounded p-3 text-sm">{issue.decline_feedback}</p>
              </div>
            )}
          </div>
        </div>

        {/* Terminal tab — always mounted when terminalId exists, just hidden */}
        {terminalId && (
          <div
            className={`rounded-b-lg shadow-sm border border-t-0 overflow-hidden ${activeTab === "terminal" ? "block h-full" : "hidden"}`}
          >
            <TerminalPanel terminalId={terminalId} onSessionEnd={() => { setTerminalId(null); setActiveTab("details"); }} />
          </div>
        )}
      </div>

      {/* Close confirmation modal */}
      {showCloseConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={(e) => { if (e.target === e.currentTarget) setShowCloseConfirm(false); }}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
            <h3 className="text-lg font-bold mb-2">Close Terminal?</h3>
            <p className="text-gray-600 text-sm mb-4">This will kill the terminal process. Any running commands will be terminated.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCloseConfirm(false)} className="px-4 py-2 rounded border hover:bg-gray-50 text-sm">Cancel</button>
              <button onClick={closeTerminal} className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 text-sm">Close Terminal</button>
            </div>
          </div>
        </div>
      )}

      {/* Limit warning modal */}
      {showLimitWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={(e) => { if (e.target === e.currentTarget) setShowLimitWarning(false); }}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
            <h3 className="text-lg font-bold mb-2 text-amber-600">Terminal Limit Reached</h3>
            <p className="text-gray-600 text-sm mb-4">You have reached the soft limit of open terminals. Consider closing unused terminals to free resources.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowLimitWarning(false)} className="px-4 py-2 rounded border hover:bg-gray-50 text-sm">Cancel</button>
              <button onClick={doOpenTerminal} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">Open Anyway</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
