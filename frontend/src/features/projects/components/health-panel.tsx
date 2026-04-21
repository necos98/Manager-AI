import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Loader2, Download, RefreshCw } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { toast } from "sonner";
import {
  useProjectHealth,
  useInstallManagerJson,
  useInstallClaudeResources,
  useInstallMcp,
} from "@/features/projects/hooks";
import { terminalKeys } from "@/features/terminals/hooks";

interface HealthPanelProps {
  projectId: string;
}

interface StatusRowProps {
  title: string;
  installed: boolean;
  detail?: string;
  action?: React.ReactNode;
}

function StatusRow({ title, installed, detail, action }: StatusRowProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border p-4">
      {installed ? (
        <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
      ) : (
        <XCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
      )}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm">{title}</div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {installed ? "Installed" : "Not installed"}
          {detail ? ` — ${detail}` : ""}
        </div>
      </div>
      {action}
    </div>
  );
}

export function HealthPanel({ projectId }: HealthPanelProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const healthQuery = useProjectHealth(projectId);
  const installManagerJson = useInstallManagerJson(projectId);
  const installClaudeResources = useInstallClaudeResources(projectId);
  const installMcp = useInstallMcp(projectId);
  const [running, setRunning] = useState(false);
  const [reinstallingResources, setReinstallingResources] = useState(false);

  const health = healthQuery.data;

  async function handleReinstallResources() {
    if (reinstallingResources) return;
    setReinstallingResources(true);
    try {
      await installClaudeResources.mutateAsync();
      toast.success("Claude Resources reinstalled");
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "health"] });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reinstall failed");
    } finally {
      setReinstallingResources(false);
    }
  }

  async function handleInstallAll() {
    if (!health || running) return;
    setRunning(true);
    try {
      if (!health.manager_json.installed) {
        await installManagerJson.mutateAsync();
      }
      await installClaudeResources.mutateAsync();
      if (!health.mcp.installed) {
        await installMcp.mutateAsync();
        toast.success("Terminal opened — run the MCP install command");
        queryClient.invalidateQueries({ queryKey: terminalKeys.all });
        queryClient.invalidateQueries({ queryKey: terminalKeys.count });
        navigate({ to: "/terminals" });
      } else {
        toast.success("Dependencies installed");
      }
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "health"] });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Install failed");
    } finally {
      setRunning(false);
    }
  }

  if (healthQuery.isLoading) {
    return (
      <div className="p-6 space-y-3 max-w-2xl">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (!health) {
    return <div className="p-6 text-sm text-destructive">Failed to load health status</div>;
  }

  const allInstalled =
    health.manager_json.installed && health.claude_resources.installed && health.mcp.installed;

  const resourcesDetail = health.claude_resources.installed
    ? health.claude_resources.path
    : health.claude_resources.missing.length
      ? `missing: ${health.claude_resources.missing.join(", ")}`
      : health.claude_resources.path;

  return (
    <div className="p-6 max-w-2xl space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">
            Check integration state for this project.
          </p>
        </div>
        <Button onClick={handleInstallAll} disabled={running || allInstalled}>
          {running ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Download className="h-4 w-4 mr-2" />
          )}
          {running ? "Installing..." : allInstalled ? "All installed" : "Install all dependencies"}
        </Button>
      </div>

      <div className="space-y-3">
        <StatusRow
          title="MCP Server"
          installed={health.mcp.installed}
          detail={health.mcp.location ?? undefined}
        />
        <StatusRow
          title="manager.json"
          installed={health.manager_json.installed}
          detail={health.manager_json.path}
        />
        <StatusRow
          title="Claude Resources"
          installed={health.claude_resources.installed}
          detail={resourcesDetail}
          action={
            health.claude_resources.installed ? (
              <Button
                size="sm"
                variant="outline"
                onClick={handleReinstallResources}
                disabled={reinstallingResources || running}
              >
                {reinstallingResources ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                )}
                {reinstallingResources ? "Reinstalling..." : "Reinstall"}
              </Button>
            ) : undefined
          }
        />
      </div>
    </div>
  );
}
