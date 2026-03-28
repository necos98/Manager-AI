import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { ProjectVariablesEditor } from "@/features/projects/components/project-variables-editor";

export const Route = createFileRoute("/projects/$projectId/variables")({
  component: VariablesPage,
});

function VariablesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Variables - ${project.name}` : "Variables";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-2">Environment Variables</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Custom variables injected into terminals for this project. Secrets are masked in the UI but sent in plain text to the terminal process.
      </p>
      <ProjectVariablesEditor projectId={projectId} />
    </div>
  );
}
