import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function ProjectCard({ project }) {
  const counts = project.issue_counts || {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <Link
      to={`/projects/${project.id}`}
      className="block bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
      <p className="text-sm text-gray-500 mt-1 font-mono">{project.path}</p>
      {project.description && (
        <p className="text-sm text-gray-600 mt-2 line-clamp-2">{project.description}</p>
      )}
      {total > 0 && (
        <div className="flex gap-2 mt-3 flex-wrap">
          {Object.entries(counts).map(([status, count]) => (
            <span key={status} className="text-xs">
              <StatusBadge status={status} /> {count}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}
