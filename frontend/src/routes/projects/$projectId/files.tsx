import { createFileRoute } from "@tanstack/react-router";
import { FileGallery } from "@/features/files/components/file-gallery";

export const Route = createFileRoute("/projects/$projectId/files")({
  component: FilesPage,
});

function FilesPage() {
  const { projectId } = Route.useParams();

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-6">Files</h1>
      <FileGallery projectId={projectId} />
    </div>
  );
}
