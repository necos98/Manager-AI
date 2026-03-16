import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import MarkdownViewer from "../components/MarkdownViewer";
import StatusBadge from "../components/StatusBadge";

export default function TaskDetailPage() {
  const { id: projectId, taskId } = useParams();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showDeclineForm, setShowDeclineForm] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState(null);

  const loadTask = () => {
    api.getTask(projectId, taskId).then(setTask).finally(() => setLoading(false));
  };

  useEffect(loadTask, [projectId, taskId]);

  const handleStatusChange = async (status, declineFeedback) => {
    try {
      const data = { status };
      if (declineFeedback) data.decline_feedback = declineFeedback;
      const updated = await api.updateTaskStatus(projectId, taskId, data);
      setTask(updated);
      setShowDeclineForm(false);
      setFeedback("");
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <p>Loading...</p>;
  if (!task) return <p>Task not found.</p>;

  return (
    <div>
      <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline mb-4 block">
        &larr; Back to tasks
      </button>

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold">{task.name || "Untitled Task"}</h1>
            <p className="text-sm text-gray-500 mt-1">Priority: {task.priority}</p>
          </div>
          <StatusBadge status={task.status} />
        </div>

        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Description</h2>
          <p className="text-gray-700">{task.description}</p>
        </div>

        {task.plan && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Plan</h2>
            <div className="bg-gray-50 rounded p-4">
              <MarkdownViewer content={task.plan} />
            </div>
          </div>
        )}

        {task.recap && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Recap</h2>
            <div className="bg-green-50 rounded p-4">
              <MarkdownViewer content={task.recap} />
            </div>
          </div>
        )}

        {task.decline_feedback && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Decline Feedback</h2>
            <p className="text-red-700 bg-red-50 rounded p-4">{task.decline_feedback}</p>
          </div>
        )}

        {error && <p className="text-red-600 mb-4">{error}</p>}

        <div className="flex gap-3 pt-4 border-t">
          {task.status === "Planned" && (
            <>
              <button
                onClick={() => handleStatusChange("Accepted")}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Accept
              </button>
              <button
                onClick={() => setShowDeclineForm(true)}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Decline
              </button>
            </>
          )}
          <button
            onClick={() => handleStatusChange("Canceled")}
            className="px-4 py-2 rounded border text-gray-600 hover:bg-gray-50"
          >
            Cancel Task
          </button>
        </div>

        {showDeclineForm && (
          <div className="mt-4 p-4 bg-red-50 rounded">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Why are you declining this task?
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full border rounded px-3 py-2 mb-2"
              rows={3}
              placeholder="Explain what needs to change..."
            />
            <div className="flex gap-2">
              <button
                onClick={() => handleStatusChange("Declined", feedback)}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Submit Decline
              </button>
              <button
                onClick={() => { setShowDeclineForm(false); setFeedback(""); }}
                className="px-4 py-2 rounded border hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
