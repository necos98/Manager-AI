import { Badge } from "@/shared/components/ui/badge";
import type { IssueStatus, TaskStatus } from "@/shared/types";

const STATUS_VARIANTS: Record<string, string> = {
  New: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  Reasoning: "bg-indigo-100 text-indigo-800 hover:bg-indigo-100",
  Planned: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100",
  Accepted: "bg-green-100 text-green-800 hover:bg-green-100",
  Finished: "bg-zinc-100 text-zinc-800 hover:bg-zinc-100",
  Canceled: "bg-zinc-100 text-zinc-500 hover:bg-zinc-100",
  Pending: "bg-slate-100 text-slate-700 hover:bg-slate-100",
  "In Progress": "bg-amber-100 text-amber-800 hover:bg-amber-100",
  Completed: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100",
};

interface StatusBadgeProps {
  status: IssueStatus | TaskStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant="secondary" className={STATUS_VARIANTS[status] || ""}>
      {status}
    </Badge>
  );
}
