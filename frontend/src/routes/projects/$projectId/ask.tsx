import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { MessageSquare } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { useAskTerminals, useCreateAskTerminal, useKillTerminal, terminalKeys } from "@/features/terminals/hooks";
import { useProject } from "@/features/projects/hooks";
import { toast } from "sonner";

export const Route = createFileRoute("/projects/$projectId/ask")({
  component: AskPage,
});

function AskPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const [terminalId, setTerminalId] = useState<string | null>(null);
  const createAskTerminal = useCreateAskTerminal();
  const killTerminal = useKillTerminal();
  const { data: askTerminals, isLoading: askTerminalsLoading } = useAskTerminals(projectId);
  const queryClient = useQueryClient();

  useEffect(() => {
    document.title = project ? `Ask & Brainstorming - ${project.name}` : "Ask & Brainstorming";
  }, [project]);

  // Reattach to an existing ask terminal for this project when the page remounts.
  useEffect(() => {
    if (terminalId) return;
    if (!askTerminals || askTerminals.length === 0) return;
    const latest = [...askTerminals].sort((a, b) =>
      (b.created_at ?? "").localeCompare(a.created_at ?? ""),
    )[0];
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (latest?.id) setTerminalId(latest.id);
  }, [askTerminals, terminalId, setTerminalId]);

  const handleStart = async () => {
    try {
      const terminal = await createAskTerminal.mutateAsync({ project_id: projectId });
      setTerminalId(terminal.id);
      queryClient.invalidateQueries({ queryKey: terminalKeys.ask(projectId) });
    } catch (err) {
      toast.error("Failed to start session: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const handleNewConversation = async () => {
    const current = terminalId;
    if (current) {
      try {
        await killTerminal.mutateAsync(current);
      } catch {
        // already gone — ignore
      }
    }
    setTerminalId(null);
    queryClient.invalidateQueries({ queryKey: terminalKeys.ask(projectId) });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          {project && (
            <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
          )}
          <h1 className="text-xl font-semibold">Ask & Brainstorming</h1>
        </div>
        {terminalId && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleNewConversation}
          >
            New conversation
          </Button>
        )}
      </div>

      {!terminalId ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 p-6">
          <MessageSquare className="size-12 text-muted-foreground" />
          <div className="text-center">
            <h2 className="text-lg font-medium mb-1">Start a brainstorming session</h2>
            <p className="text-sm text-muted-foreground max-w-md">
              Claude will load your project context and help you think through ideas, architectural decisions, and creative directions. You can also ask it to create issues.
            </p>
          </div>
          <Button
            onClick={handleStart}
            disabled={createAskTerminal.isPending || askTerminalsLoading}
          >
            {createAskTerminal.isPending ? "Starting..." : "Start conversation"}
          </Button>
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <TerminalPanel
            terminalId={terminalId}
            projectId={projectId}
            onSessionEnd={handleNewConversation}
          />
        </div>
      )}
    </div>
  );
}
