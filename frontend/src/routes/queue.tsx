import { createFileRoute, Link } from "@tanstack/react-router";
import { useGlobalQueue, useGlobalRunning, useSetAutoProcess, useRemoveFromQueue } from "@/features/queue/hooks";
import { useQueueStatus } from "@/features/queue/hooks";
import { useEvents, type WsEventData } from "@/shared/context/event-context";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Switch } from "@/shared/components/ui/switch";
import { useEffect, useState } from "react";
import { queueKeys } from "@/features/queue/hooks";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Trash2, Loader2 } from "lucide-react";

export const Route = createFileRoute("/queue")({
  component: QueuePage,
});

function QueuePage() {
  const { data: queuedData, isLoading: queueLoading } = useGlobalQueue();
  const { data: runningData, isLoading: runningLoading } = useGlobalRunning();
  const { data: statusData } = useQueueStatus();
  const events = useEvents();
  const queryClient = useQueryClient();
  const removeFromQueue = useRemoveFromQueue();
  const [removeConfirm, setRemoveConfirm] = useState<{ projectId: string; issueId: string; issueName: string } | null>(null);

  // Subscribe to WebSocket events for real-time invalidation
  useEffect(() => {
    if (!events) return;
    const unsubscribe = events.subscribe((event: WsEventData) => {
      if (event.type === "issue_status_changed") {
        const ns = event.new_status;
        if (ns === "Queued" || ns === "Reasoning" || ns === "Finished") {
          queryClient.invalidateQueries({ queryKey: queueKeys.queued });
          queryClient.invalidateQueries({ queryKey: queueKeys.status });
        }
      }
      if (event.type === "terminal_created" || event.type === "terminal_closed") {
        queryClient.invalidateQueries({ queryKey: queueKeys.running });
        queryClient.invalidateQueries({ queryKey: queueKeys.status });
      }
    });
    return unsubscribe;
  }, [events, queryClient]);

  const isLoading = queueLoading && runningLoading;

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  const queued = queuedData?.queued ?? [];
  const running = runningData?.running ?? [];
  const isPaused = statusData?.paused ?? false;
  const isAutoProcessEnabled = statusData?.auto_process_enabled ?? false;
  const setAutoProcess = useSetAutoProcess();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Issue Queue</h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {isPaused && (
            <span className="text-amber-600 dark:text-amber-400 font-medium">
              ⏸ Paused
            </span>
          )}
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <Switch
              checked={isAutoProcessEnabled}
              onCheckedChange={(checked) => setAutoProcess.mutate(checked)}
              disabled={setAutoProcess.isPending}
            />
            <span className={isAutoProcessEnabled ? "text-emerald-500 font-medium" : "text-muted-foreground"}>
              Auto-process
            </span>
          </label>
          <span>{running.length} running</span>
          <span>{queued.length} queued</span>
        </div>
      </div>

      {/* In esecuzione */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              {running.length > 0 && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
              <span
                className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  running.length > 0 ? "bg-emerald-500" : "bg-muted-foreground/30"
                }`}
              />
            </span>
            In esecuzione
          </CardTitle>
        </CardHeader>
        <CardContent>
          {running.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">
              Nessuna issue in esecuzione
            </p>
          ) : (
            <ul className="space-y-2">
              {running.map((item) => (
                <li key={item.terminal_id}>
                  <Link
                    to="/projects/$projectId/issues/$issueId"
                    params={{ projectId: item.project_id, issueId: item.issue_id }}
                    className="flex items-center gap-2 text-sm hover:underline py-1"
                  >
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                    </span>
                    <span className="font-medium truncate max-w-[300px]">
                      {item.issue_name || "(unnamed)"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      in {item.project_name || item.project_id}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* In coda */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            In coda
            {queued.length > 0 && (
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({queued.length} issue{queued.length !== 1 ? "" : ""})
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {queued.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">
              Nessuna issue in coda
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-xs uppercase tracking-wider">
                    <th className="text-left py-2 pr-2 w-12">#</th>
                    <th className="text-left py-2 px-2">Issue</th>
                    <th className="text-left py-2 px-2">Project</th>
                    <th className="text-right py-2 pl-2">Created</th>
                    <th className="text-right py-2 pl-2 w-20">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {queued.map((item) => (
                    <tr
                      key={item.issue_id}
                      className={`border-b last:border-0 hover:bg-muted/50 ${
                        item.position === 1 ? "font-medium" : ""
                      }`}
                    >
                      <td className="py-2 pr-2 text-muted-foreground">
                        {item.position === 1 ? (
                          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs">
                            {item.position}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">{item.position}</span>
                        )}
                      </td>
                      <td className="py-2 px-2">
                        <Link
                          to="/projects/$projectId/issues/$issueId"
                          params={{ projectId: item.project_id, issueId: item.issue_id }}
                          className="hover:underline"
                        >
                          {item.issue_name || item.issue_description || "(unnamed)"}
                        </Link>
                      </td>
                      <td className="py-2 px-2">
                        <Link
                          to="/projects/$projectId/issues"
                          params={{ projectId: item.project_id }}
                          className="text-muted-foreground hover:underline"
                        >
                          {item.project_name}
                        </Link>
                      </td>
                      <td className="py-2 pl-2 text-right text-muted-foreground text-xs">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 pl-2 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() =>
                            setRemoveConfirm({
                              projectId: item.project_id,
                              issueId: item.issue_id,
                              issueName: item.issue_name || item.issue_description || "(unnamed)",
                            })
                          }
                          disabled={removeFromQueue.isPending}
                          aria-label="Remove from queue"
                        >
                          <Trash2 className="size-3" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Remove confirmation */}
      <Dialog open={removeConfirm !== null} onOpenChange={() => setRemoveConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove from Queue?</DialogTitle>
            <DialogDescription>
              Remove <span className="font-medium">{removeConfirm?.issueName}</span> from the queue.
              The issue itself will not be affected.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={removeFromQueue.isPending}
              onClick={() => {
                if (!removeConfirm) return;
                removeFromQueue.mutate(
                  { projectId: removeConfirm.projectId, issueId: removeConfirm.issueId },
                  {
                    onSuccess: () => setRemoveConfirm(null),
                  },
                );
              }}
            >
              {removeFromQueue.isPending ? (
                <>
                  <Loader2 className="size-4 mr-1 animate-spin" />
                  Removing...
                </>
              ) : (
                "Remove"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
