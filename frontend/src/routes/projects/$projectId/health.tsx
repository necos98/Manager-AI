import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { HealthPanel } from "@/features/projects/components/health-panel";

export const Route = createFileRoute("/projects/$projectId/health")({
  component: HealthPage,
});

function HealthPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Health - ${project.name}` : "Health";
  }, [project]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        {project && <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>}
        <h1 className="text-xl font-semibold">Health</h1>
      </div>
      <div className="flex-1 overflow-auto">
        <HealthPanel projectId={projectId} />
      </div>
    </div>
  );
}
