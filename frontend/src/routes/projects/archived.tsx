import { createFileRoute, Link } from "@tanstack/react-router";
import { ArchiveRestore, FolderKanban } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { useProjects, useUnarchiveProject } from "@/features/projects/hooks";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/archived")({
  component: ArchivedProjectsPage,
});

function ArchivedProjectsPage() {
  const { data: projects, isLoading } = useProjects(true);
  const unarchive = useUnarchiveProject();

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  const handleUnarchive = (projectId: string, name: string) => {
    unarchive.mutate(projectId, {
      onSuccess: () => toast.success(`"${name}" restored`),
    });
  };

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <p className="text-sm text-muted-foreground mb-0.5">Projects</p>
        <h1 className="text-xl font-semibold">Archived</h1>
      </div>

      {projects && projects.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <FolderKanban className="size-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No archived projects.</p>
          <Link to="/" className="text-sm text-primary underline mt-2 inline-block">
            Back to dashboard
          </Link>
        </div>
      ) : (
        <ul className="divide-y rounded-lg border">
          {projects?.map((project) => (
            <li
              key={project.id}
              className="flex items-center justify-between gap-3 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="font-medium truncate">{project.name}</p>
                <p className="text-xs text-muted-foreground font-mono truncate">
                  {project.path}
                </p>
                {project.archived_at && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    archived{" "}
                    {formatDistanceToNow(new Date(project.archived_at), {
                      addSuffix: true,
                    })}
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={unarchive.isPending && unarchive.variables === project.id}
                onClick={() => handleUnarchive(project.id, project.name)}
              >
                <ArchiveRestore className="size-3.5 mr-1.5" />
                {unarchive.isPending && unarchive.variables === project.id
                  ? "Restoring..."
                  : "Unarchive"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
