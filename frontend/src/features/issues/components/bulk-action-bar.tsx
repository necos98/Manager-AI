import { useState } from "react";
import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useUpdateIssueStatus } from "@/features/issues/hooks";
import type { Issue, IssueStatus } from "@/shared/types";

const TARGET_STATUSES: IssueStatus[] = [
  "New",
  "Reasoning",
  "Planned",
  "Accepted",
  "Canceled",
  "Finished",
];

interface BulkActionBarProps {
  projectId: string;
  selectedIssueIds: Set<string>;
  allIssues: Issue[];
  onComplete: () => void;
}

export function BulkActionBar({
  projectId,
  selectedIssueIds,
  allIssues,
  onComplete,
}: BulkActionBarProps) {
  const [targetStatus, setTargetStatus] = useState<IssueStatus | "">("");
  const updateStatus = useUpdateIssueStatus(projectId);

  const selectedIssues = allIssues.filter((i) => selectedIssueIds.has(i.id));
  const count = selectedIssues.length;

  const handleApply = () => {
    if (!targetStatus) return;
    for (const issue of selectedIssues) {
      updateStatus.mutate({ issueId: issue.id, status: targetStatus });
    }
    onComplete();
    setTargetStatus("");
  };

  return (
    <div className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-lg border bg-background px-4 py-3 shadow-lg">
      <span className="text-sm font-medium whitespace-nowrap">
        {count} selected
      </span>

      <Select value={targetStatus} onValueChange={(v) => setTargetStatus(v as IssueStatus)}>
        <SelectTrigger className="w-36">
          <SelectValue placeholder="Move to..." />
        </SelectTrigger>
        <SelectContent>
          {TARGET_STATUSES.map((s) => (
            <SelectItem key={s} value={s}>
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button size="sm" onClick={handleApply} disabled={!targetStatus}>
        Apply
      </Button>

      <Button variant="ghost" size="sm" onClick={onComplete}>
        Cancel
      </Button>
    </div>
  );
}
