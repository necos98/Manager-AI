import { createFileRoute, Outlet } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId")({
  component: ProjectLayout,
});

function ProjectLayout() {
  const { projectId } = Route.useParams();
  const { data: project, isLoading, error } = useProject(projectId);

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-6">
        <p className="text-destructive">Project not found.</p>
      </div>
    );
  }

  return <Outlet />;
}
