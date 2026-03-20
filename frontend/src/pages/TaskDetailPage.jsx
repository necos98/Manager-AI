import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import MarkdownViewer from "../components/MarkdownViewer";
import StatusBadge from "../components/StatusBadge";
import TerminalPanel from "../components/TerminalPanel";

function SplitView({ terminalId, onSessionEnd, leftPanel }) {
  const containerRef = useRef(null);
  const [leftWidth, setLeftWidth] = useState(40);
  const dragging = useRef(false);

  const onMouseDown = useCallback((e) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftWidth(Math.min(Math.max(pct, 20), 80));
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div ref={containerRef} className="flex bg-white rounded-lg shadow-sm border" style={{ height: "calc(100vh - 160px)" }}>
      <div className="overflow-y-auto" style={{ width: `${leftWidth}%` }}>
        {leftPanel}
      </div>
      <div
        className="w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize flex-shrink-0 transition-colors"
        onMouseDown={onMouseDown}
      />
      <div className="flex-1 min-w-0">
        <TerminalPanel terminalId={terminalId} onSessionEnd={onSessionEnd} />
      </div>
    </div>
  );
}

export default function TaskDetailPage() {
  const { id: projectId, taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [terminalId, setTerminalId] = useState(null);
  const [terminalLoading, setTerminalLoading] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [showLimitWarning, setShowLimitWarning] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getTask(projectId, taskId),
      api.listTerminals(null, taskId),
    ]).then(([t, terminals]) => {
      setTask(t);
      if (terminals.length > 0) {
        setTerminalId(terminals[0].id);
      }
    }).finally(() => setLoading(false));
  }, [projectId, taskId]);

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
      const term = await api.createTerminal(taskId, projectId);
      setTerminalId(term.id);
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
    }
  };

  if (loading) return <p>Loading...</p>;
  if (!task) return <p>Task not found.</p>;

  const taskDetails = (
    <div className={terminalId ? "overflow-y-auto p-4" : "p-6"}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h1 className={`font-bold ${terminalId ? "text-lg" : "text-2xl"}`}>
            {task.name || "Untitled Task"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">Priority: {task.priority}</p>
        </div>
        <StatusBadge status={task.status} />
      </div>

      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Description</h2>
        <p className="text-gray-700 text-sm">{task.description}</p>
      </div>

      {task.specification && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Specification</h2>
          <div className="bg-indigo-50 rounded p-3">
            <MarkdownViewer content={task.specification} />
          </div>
        </div>
      )}

      {task.plan && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Plan</h2>
          <div className="bg-gray-50 rounded p-3">
            <MarkdownViewer content={task.plan} />
          </div>
        </div>
      )}

      {task.recap && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Recap</h2>
          <div className="bg-green-50 rounded p-3">
            <MarkdownViewer content={task.recap} />
          </div>
        </div>
      )}

      {task.decline_feedback && (
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Decline Feedback</h2>
          <p className="text-red-700 bg-red-50 rounded p-3 text-sm">{task.decline_feedback}</p>
        </div>
      )}
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to tasks
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

      {terminalId ? (
        <SplitView
          terminalId={terminalId}
          onSessionEnd={() => setTerminalId(null)}
          leftPanel={taskDetails}
        />
      ) : (
        <div className="bg-white rounded-lg shadow-sm border">
          {taskDetails}
        </div>
      )}

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
