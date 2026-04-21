import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { MessageSquare } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { useCreateAskTerminal } from "@/features/terminals/hooks";
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

  useEffect(() => {
    document.title = project ? `Ask & Brainstorming - ${project.name}` : "Ask & Brainstorming";
  }, [project]);

  const handleStart = async () => {
    try {
      const terminal = await createAskTerminal.mutateAsync({ project_id: projectId });
      setTerminalId(terminal.id);
    } catch (err) {
      toast.error("Failed to start session: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const handleNewConversation = () => {
    setTerminalId(null);
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
            disabled={createAskTerminal.isPending}
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
