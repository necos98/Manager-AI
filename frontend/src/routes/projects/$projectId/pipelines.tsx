import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PipelinesTab } from "@/features/pipelines/components/PipelinesTab";
import { useProject } from "@/features/projects/hooks";

export const Route = createFileRoute("/projects/$projectId/pipelines")({
  component: PipelinesPage,
});

function PipelinesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    if (project) document.title = `Pipelines — ${project.name}`;
  }, [project]);

  return <PipelinesTab projectId={projectId} />;
}
