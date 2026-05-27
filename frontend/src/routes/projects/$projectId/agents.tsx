import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AgentsTab } from "@/features/agents/components/AgentsTab";
import { useProject } from "@/features/projects/hooks";

export const Route = createFileRoute("/projects/$projectId/agents")({
  component: AgentsPage,
});

function AgentsPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    if (project) document.title = `Agents — ${project.name}`;
  }, [project]);

  return <AgentsTab projectId={projectId} />;
}
