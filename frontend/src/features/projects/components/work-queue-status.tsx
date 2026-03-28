import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEvents, type WsEventData } from "@/shared/context/event-context";
import { fetchSettings, updateSetting } from "@/features/settings/api";
import { settingKeys } from "@/features/settings/hooks";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface WorkQueueStatusProps {
  projectId: string;
}

interface ActiveHook {
  description: string;
  issueName: string;
}

export function WorkQueueStatus({ projectId }: WorkQueueStatusProps) {
  const events = useEvents();
  const queryClient = useQueryClient();
  const [activeHook, setActiveHook] = useState<ActiveHook | null>(null);

  const { data: settings, isLoading } = useQuery({
    queryKey: settingKeys.all,
    queryFn: fetchSettings,
  });

  const pauseMutation = useMutation({
    mutationFn: (paused: boolean) =>
      updateSetting("work_queue_paused", paused ? "true" : "false"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
  });

  const isPaused =
    settings?.find((s) => s.key === "work_queue_paused")?.value === "true";

  useEffect(() => {
    if (!events) return;
    const unsubscribe = events.subscribe((event: WsEventData) => {
      if (event.project_id !== projectId) return;

      if (event.type === "hook_started") {
        setActiveHook({
          description: (event.message as string) || "Lavorando...",
          issueName: (event.issue_name as string) || "",
        });
      } else if (
        event.type === "hook_completed" ||
        event.type === "hook_failed"
      ) {
        setActiveHook(null);
      }
    });
    return unsubscribe;
  }, [events, projectId]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  const saving = pauseMutation.isPending;

  return (
    <div className="space-y-4">
      {/* Paused banner */}
      {isPaused && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          <span className="font-medium">Coda in pausa</span> — nessun nuovo hook
          verrà avviato finché non viene ripresa.
        </div>
      )}

      {/* Active hook indicator */}
      <div className="border rounded-lg p-4 space-y-2">
        <p className="text-sm font-medium">Stato coda di lavoro</p>
        {activeHook ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            <span>
              <span className="font-medium">Claude sta lavorando:</span>{" "}
              {activeHook.description}
              {activeHook.issueName && (
                <>
                  {" su "}
                  <span className="font-medium">{activeHook.issueName}</span>
                </>
              )}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-muted-foreground/30" />
            </span>
            <span>Nessun hook in esecuzione</span>
          </div>
        )}
      </div>

      {/* Pause / Resume button */}
      <div className="border rounded-lg p-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <button
            role="switch"
            aria-checked={!isPaused}
            onClick={() => pauseMutation.mutate(!isPaused)}
            disabled={saving}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none flex-shrink-0 ${
              !isPaused ? "bg-primary" : "bg-input"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                !isPaused ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <div>
            <p className="font-medium text-sm">Coda di lavoro attiva</p>
            <p className="text-xs text-muted-foreground">
              {isPaused
                ? "La coda è in pausa — premi per riprendere"
                : "La coda è attiva — premi per mettere in pausa"}
            </p>
          </div>
        </label>
        {saving && (
          <p className="text-xs text-muted-foreground mt-2 pl-14">
            Salvataggio in corso...
          </p>
        )}
      </div>
    </div>
  );
}
