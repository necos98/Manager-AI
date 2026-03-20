const STATUS_COLORS = {
  // Issue statuses
  New: "bg-blue-100 text-blue-800",
  Reasoning: "bg-indigo-100 text-indigo-800",
  Planned: "bg-yellow-100 text-yellow-800",
  Accepted: "bg-green-100 text-green-800",
  Declined: "bg-red-100 text-red-800",
  Finished: "bg-gray-100 text-gray-800",
  Canceled: "bg-gray-100 text-gray-500",
  // Task statuses
  Pending: "bg-slate-100 text-slate-700",
  "In Progress": "bg-amber-100 text-amber-800",
  Completed: "bg-emerald-100 text-emerald-800",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[status] || "bg-gray-100"}`}>
      {status}
    </span>
  );
}
