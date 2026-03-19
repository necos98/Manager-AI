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

  useEffect(() => {
    api.getTask(projectId, taskId).then(setTask).finally(() => setLoading(false));
  }, [projectId, taskId]);

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

        {task.specification && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Specification</h2>
            <div className="bg-indigo-50 rounded p-4">
              <MarkdownViewer content={task.specification} />
            </div>
          </div>
        )}

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
      </div>
    </div>
  );
}
