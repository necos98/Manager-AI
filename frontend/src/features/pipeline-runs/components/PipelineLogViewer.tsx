import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Bug,
  ChevronDown,
  ChevronRight,
  Loader2,
  FileText,
} from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/shared/components/ui/collapsible";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { usePipelineLogsByIssue, usePipelineRuns } from "@/features/pipeline-runs/hooks";
import type { PipelineLogEntry } from "@/shared/types";

interface PipelineLogViewerProps {
  projectId: string;
  issueId: string;
}

const LEVEL_CONFIG = {
  ERROR: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50 dark:bg-red-950/20", border: "border-red-200 dark:border-red-800" },
  WARN: { icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-50 dark:bg-amber-950/20", border: "border-amber-200 dark:border-amber-800" },
  INFO: { icon: Info, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-950/10", border: "border-blue-200 dark:border-blue-800" },
  DEBUG: { icon: Bug, color: "text-gray-400", bg: "bg-gray-50 dark:bg-gray-900/10", border: "border-gray-200 dark:border-gray-700" },
} as const;

function LevelIcon({ level }: { level: string }) {
  const cfg = LEVEL_CONFIG[level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.INFO;
  const Icon = cfg.icon;
  return <Icon className={`size-4 shrink-0 ${cfg.color}`} />;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 10) return "just now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function PipelineLogViewer({ projectId, issueId }: PipelineLogViewerProps) {
  const [levelFilter, setLevelFilter] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string>("all");

  const { data: runs } = usePipelineRuns(projectId, issueId);
  const activeRun = runs?.find((r) => r.status === "RUNNING");
  const isPipelineActive = !!activeRun;

  const { data: logsData, isLoading } = usePipelineLogsByIssue(
    projectId,
    issueId,
    levelFilter ?? undefined,
    { refetchInterval: isPipelineActive ? 3000 : false },
  );

  const logs = logsData?.logs ?? [];

  // Filter by selected run
  const filtered = selectedRunId === "all"
    ? logs
    : logs.filter((l) => l.pipeline_run_id === selectedRunId);

  // Group by source
  const sourceCounts: Record<string, number> = {};
  for (const l of logs) {
    sourceCounts[l.source] = (sourceCounts[l.source] || 0) + 1;
  }

  const levelCounts: Record<string, number> = {};
  for (const l of logs) {
    levelCounts[l.level] = (levelCounts[l.level] || 0) + 1;
  }

  const LEVELS = ["ERROR", "WARN", "INFO", "DEBUG"] as const;

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-3/4" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Run selector */}
        {runs && runs.length > 1 && (
          <Select value={selectedRunId} onValueChange={setSelectedRunId}>
            <SelectTrigger className="h-8 w-44 text-xs">
              <SelectValue placeholder="All runs" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All runs ({logs.length})</SelectItem>
              {runs.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  Run #{r.id.slice(0, 8)} — {r.status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Level filter pills */}
        {LEVELS.map((lvl) => {
          const count = levelCounts[lvl] ?? 0;
          const cfg = LEVEL_CONFIG[lvl];
          const active = levelFilter === lvl;
          return (
            <Button
              key={lvl}
              variant={active ? "default" : "outline"}
              size="sm"
              className={`h-7 text-xs gap-1 ${active ? "" : cfg.color}`}
              onClick={() => setLevelFilter(active ? null : lvl)}
            >
              <cfg.icon className="size-3" />
              {lvl}
              {count > 0 && (
                <span className="opacity-70">({count})</span>
              )}
            </Button>
          );
        })}

        {/* Clear filter */}
        {levelFilter && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setLevelFilter(null)}
          >
            Clear
          </Button>
        )}

        {isPipelineActive && (
          <span className="text-xs text-muted-foreground flex items-center gap-1 ml-auto">
            <Loader2 className="size-3 animate-spin" />
            Live
          </span>
        )}
      </div>

      {/* Log entries */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <FileText className="size-8 mb-2 opacity-40" />
          <p className="text-sm">No log entries{levelFilter ? " for this level" : ""}</p>
        </div>
      ) : (
        <ScrollArea className="max-h-[500px]">
          <div className="space-y-1 pr-2">
            {filtered.map((entry) => (
              <LogEntryRow key={entry.id} entry={entry} />
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}

function LogEntryRow({ entry }: { entry: PipelineLogEntry }) {
  const [open, setOpen] = useState(false);
  const cfg = LEVEL_CONFIG[entry.level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.INFO;
  const hasDetails = Object.keys(entry.details).length > 0;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button
          className={`w-full flex items-start gap-2 p-2 rounded-md text-left text-sm border transition-colors hover:bg-accent/50 ${cfg.bg} ${cfg.border}`}
        >
          <div className="mt-0.5 shrink-0">
            {hasDetails ? (
              open ? <ChevronDown className="size-3.5 text-muted-foreground" /> : <ChevronRight className="size-3.5 text-muted-foreground" />
            ) : (
              <LevelIcon level={entry.level} />
            )}
          </div>
          {hasDetails && <LevelIcon level={entry.level} />}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-medium text-muted-foreground">
                {entry.source}
              </span>
              <Badge
                variant="outline"
                className={`text-[10px] px-1 py-0 h-4 ${cfg.color} ${cfg.border}`}
              >
                {entry.level}
              </Badge>
              <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                {timeAgo(entry.created_at)}
              </span>
            </div>
            <div className="mt-0.5 text-sm break-words">
              {entry.message}
            </div>
          </div>
        </button>
      </CollapsibleTrigger>
      {hasDetails && (
        <CollapsibleContent className="px-3 pb-2">
          <pre className="text-xs text-muted-foreground bg-muted/50 rounded p-2 overflow-x-auto mt-1">
            {JSON.stringify(entry.details, null, 2)}
          </pre>
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}
