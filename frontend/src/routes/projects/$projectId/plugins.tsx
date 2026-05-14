import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { PluginsPanel } from "@/features/settings/components/plugins-panel";

export const Route = createFileRoute("/projects/$projectId/plugins")({
  component: PluginsPage,
});

function PluginsPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `MCP Plugins - ${project.name}` : "MCP Plugins";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-2">MCP Plugins</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Connect external MCP servers (databases, APIs, etc.) as plugins. Tools are exposed through the Manager AI endpoint with <code className="text-xs bg-muted px-1 rounded">plugin__tool</code> naming.
      </p>
      <PluginsPanel projectId={projectId} />
    </div>
  );
}
