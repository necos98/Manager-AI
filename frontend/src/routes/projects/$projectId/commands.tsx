import { createFileRoute } from "@tanstack/react-router";
import { TerminalCommandsEditor } from "@/features/terminals/components/terminal-commands-editor";

export const Route = createFileRoute("/projects/$projectId/commands")({
  component: CommandsPage,
});

function CommandsPage() {
  const { projectId } = Route.useParams();

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-2">Terminal Commands</h1>
      <p className="text-sm text-muted-foreground mb-6">
        These commands run when opening a terminal for this project. When set, they override the global terminal commands.
      </p>
      <TerminalCommandsEditor projectId={projectId} />
    </div>
  );
}
