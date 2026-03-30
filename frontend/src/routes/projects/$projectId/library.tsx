// frontend/src/routes/projects/$projectId/library.tsx
import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { LibraryTab } from "@/features/projects/components/library-tab";

export const Route = createFileRoute("/projects/$projectId/library")({
  component: ProjectLibraryPage,
});

function ProjectLibraryPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Library - ${project.name}` : "Library";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-6">Library</h1>
      <div className="max-w-4xl">
        <LibraryTab projectId={projectId} />
      </div>
    </div>
  );
}
