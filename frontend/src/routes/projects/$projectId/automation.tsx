import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { AutomationPanel } from "@/features/projects/components/automation-panel";

export const Route = createFileRoute("/projects/$projectId/automation")({
  component: AutomationPage,
});

function AutomationPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Automation - ${project.name}` : "Automation";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-6">Automazione</h1>
      <div className="max-w-2xl">
        <AutomationPanel projectId={projectId} />
      </div>
    </div>
  );
}
