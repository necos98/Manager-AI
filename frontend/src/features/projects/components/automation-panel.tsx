import { useEffect, useState } from "react";
import { useProjectSettings, useSetProjectSetting } from "@/features/projects/hooks-settings";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface AutomationPanelProps {
  projectId: string;
}

export function AutomationPanel({ projectId }: AutomationPanelProps) {
  const { data: settings, isLoading, error } = useProjectSettings(projectId);
  const setSetting = useSetProjectSetting(projectId);
  const [promptDraft, setPromptDraft] = useState("");
  const [timeoutDraft, setTimeoutDraft] = useState("600");

  useEffect(() => {
    if (settings) {
      setPromptDraft(settings.auto_workflow_prompt ?? "");
      setTimeoutDraft(settings.auto_workflow_timeout ?? "600");
    }
  }, [settings]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{(error as Error).message}</p>;
  }

  const s = settings ?? {};

  const autoWorkflow = s.auto_workflow_enabled === "true";
  const autoImpl = s.auto_implementation_enabled === "true";
  const autoCompleteMode = s.auto_complete_mode ?? "off";

  const toggle = (key: string, current: boolean) => {
    setSetting.mutate({ key, value: current ? "false" : "true" });
  };

  const updateText = (key: string, value: string) => {
    setSetting.mutate({ key, value });
  };

  const saving = setSetting.isPending;

  return (
    <div className="space-y-5">
      {/* Auto workflow */}
      <div className="border rounded-lg p-4 space-y-3">
        <label className="flex items-center gap-3 cursor-pointer">
          <button
            role="switch"
            aria-checked={autoWorkflow}
            onClick={() => toggle("auto_workflow_enabled", autoWorkflow)}
            disabled={saving}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none flex-shrink-0 ${
              autoWorkflow ? "bg-primary" : "bg-input"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoWorkflow ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <div>
            <p className="font-medium text-sm">Auto-start workflow</p>
            <p className="text-xs text-muted-foreground">
              Avvia automaticamente spec + piano + task alla creazione dell'issue
            </p>
          </div>
        </label>

        {autoWorkflow && (
          <div className="space-y-3 pt-2 pl-14">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Prompt custom (vuoto = default)
              </label>
              <textarea
                rows={4}
                value={promptDraft}
                onChange={(e) => setPromptDraft(e.target.value)}
                onBlur={() => updateText("auto_workflow_prompt", promptDraft)}
                placeholder="{{issue_description}} {{project_name}} {{project_description}} {{tech_stack}}"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Timeout secondi (default 600)
              </label>
              <input
                type="number"
                value={timeoutDraft}
                onChange={(e) => setTimeoutDraft(e.target.value)}
                onBlur={() => updateText("auto_workflow_timeout", timeoutDraft)}
                min={60}
                max={3600}
                className="w-32 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        )}
      </div>

      {/* Auto implementation */}
      <div className="border rounded-lg p-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <button
            role="switch"
            aria-checked={autoImpl}
            onClick={() => toggle("auto_implementation_enabled", autoImpl)}
            disabled={saving}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none flex-shrink-0 ${
              autoImpl ? "bg-primary" : "bg-input"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoImpl ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <div>
            <p className="font-medium text-sm">Auto-start implementazione</p>
            <p className="text-xs text-muted-foreground">
              Avvia automaticamente l'implementazione all'accettazione dell'issue
            </p>
          </div>
        </label>
      </div>

      {/* Auto complete mode */}
      <div className="border rounded-lg p-4">
        <label className="text-sm font-medium block mb-2">Completamento automatico</label>
        <select
          value={autoCompleteMode}
          onChange={(e) => updateText("auto_complete_mode", e.target.value)}
          disabled={saving}
          className="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="off">Disabilitato</option>
          <option value="notify">Notifica utente</option>
          <option value="auto">Auto-completa con recap (Claude)</option>
        </select>
        <p className="text-xs text-muted-foreground mt-1.5">
          Comportamento quando un'issue viene completata dall'automazione
        </p>
      </div>

      {saving && (
        <p className="text-xs text-muted-foreground">Salvataggio in corso...</p>
      )}
    </div>
  );
}
