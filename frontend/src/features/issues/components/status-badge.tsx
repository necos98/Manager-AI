import { Badge } from "@/shared/components/ui/badge";
import type { IssueStatus, TaskStatus } from "@/shared/types";

const STATUS_VARIANTS: Record<string, string> = {
  New: "bg-blue-100 text-blue-800 hover:bg-blue-100 dark:bg-blue-900/40 dark:text-blue-300",
  Reasoning: "bg-indigo-100 text-indigo-800 hover:bg-indigo-100 dark:bg-indigo-900/40 dark:text-indigo-300",
  Planned: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 dark:bg-yellow-900/40 dark:text-yellow-300",
  Accepted: "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900/40 dark:text-green-300",
  Finished: "bg-zinc-100 text-zinc-800 hover:bg-zinc-100 dark:bg-zinc-800 dark:text-zinc-300",
  Canceled: "bg-zinc-100 text-zinc-500 hover:bg-zinc-100 dark:bg-zinc-800/50 dark:text-zinc-400",
  Pending: "bg-slate-100 text-slate-700 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300",
  "In Progress": "bg-amber-100 text-amber-800 hover:bg-amber-100 dark:bg-amber-900/40 dark:text-amber-300",
  Completed: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-900/40 dark:text-emerald-300",
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
