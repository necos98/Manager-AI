import type { ElementType } from "react";
import { formatDistanceToNow } from "date-fns";
import {
  CheckCircle,
  XCircle,
  FileText,
  GitBranch,
  PlayCircle,
  Zap,
  ZapOff,
  Bell,
  Activity,
} from "lucide-react";
import type { ActivityLog } from "@/shared/types";

const EVENT_CONFIG: Record<string, { label: string; Icon: ElementType; className: string }> = {
  spec_created:      { label: "Spec written",      Icon: FileText,   className: "text-blue-500" },
  plan_created:      { label: "Plan written",       Icon: GitBranch,  className: "text-purple-500" },
  issue_accepted:    { label: "Plan accepted",      Icon: CheckCircle,className: "text-green-500" },
  issue_completed:   { label: "Issue completed",    Icon: CheckCircle,className: "text-green-600" },
  issue_canceled:    { label: "Issue canceled",     Icon: XCircle,    className: "text-gray-400" },
  analysis_started:  { label: "Analysis started",   Icon: PlayCircle, className: "text-indigo-500" },
  hook_completed:    { label: "Hook completed",     Icon: Zap,        className: "text-green-500" },
  hook_failed:       { label: "Hook failed",        Icon: ZapOff,     className: "text-red-500" },
  notification:      { label: "Notification",       Icon: Bell,       className: "text-blue-400" },
};

function getConfig(eventType: string) {
  return EVENT_CONFIG[eventType] ?? { label: eventType, Icon: Activity, className: "text-muted-foreground" };
}

interface ActivityTimelineProps {
  logs: ActivityLog[];
}

export function ActivityTimeline({ logs }: ActivityTimelineProps) {
  if (logs.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        No activity yet.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {logs.map((log) => {
        const { label, Icon, className } = getConfig(log.event_type);
        const issueName = log.details.issue_name as string | undefined;
        const hookName = log.details.hook_name as string | undefined;
        const errorMsg = log.details.error as string | undefined;

        return (
          <div key={log.id} className="flex gap-3 px-3 py-2.5 rounded-md hover:bg-muted/50 transition-colors">
            <div className={`mt-0.5 shrink-0 ${className}`}>
              <Icon className="size-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium truncate">
                  {label}
                  {hookName && ` — ${hookName}`}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                </span>
              </div>
              {issueName && (
                <div className="text-xs text-muted-foreground truncate">{issueName}</div>
              )}
              {errorMsg && (
                <div className="text-xs text-red-500 truncate">{errorMsg}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
