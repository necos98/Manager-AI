import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function IssueList({ issues, projectId, activeTerminalIssueIds = [] }) {
  if (issues.length === 0) return <p className="text-gray-500">No issues yet.</p>;

  return (
    <div className="space-y-2">
      {issues.map((issue) => {
        const hasTerminal = activeTerminalIssueIds.includes(issue.id);
        return (
          <Link
            key={issue.id}
            to={`/projects/${projectId}/issues/${issue.id}`}
            className="flex items-center justify-between bg-white rounded border p-3 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-center flex-1 min-w-0">
              {hasTerminal && (
                <span
                  className="w-2 h-2 rounded-full bg-green-400 mr-3 flex-shrink-0"
                  style={{ boxShadow: "0 0 6px #4ade80" }}
                  title="Terminal active"
                />
              )}
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">{issue.name || issue.description}</p>
                {issue.name && <p className="text-sm text-gray-500 truncate">{issue.description}</p>}
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              {hasTerminal && (
                <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">terminal</span>
              )}
              <span className="text-sm text-gray-400">P{issue.priority}</span>
              <StatusBadge status={issue.status} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
