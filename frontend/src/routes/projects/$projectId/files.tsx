import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { FileGallery } from "@/features/files/components/file-gallery";

export const Route = createFileRoute("/projects/$projectId/files")({
  component: FilesPage,
});

function FilesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Files - ${project.name}` : "Files";
  }, [project]);

  return (
    <div className="p-6">
      {project && (
        <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
      )}
      <h1 className="text-xl font-semibold mb-6">Files</h1>
      <FileGallery projectId={projectId} />
    </div>
  );
}
