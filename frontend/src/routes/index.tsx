import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useProjects } from "@/features/projects/hooks";
import { Button } from "@/shared/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { StatusBadge } from "@/features/issues/components/status-badge";
import type { IssueStatus } from "@/shared/types";

export const Route = createFileRoute("/")({
  component: ProjectsPage,
});

function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Button asChild>
          <Link to="/projects/new">
            <Plus className="size-4 mr-2" />
            New Project
          </Link>
        </Button>
      </div>

      {!projects || projects.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No projects yet.</p>
          <Button asChild variant="outline">
            <Link to="/projects/new">Create your first project</Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {projects.map((project) => {
            const counts = project.issue_counts || {};
            const total = Object.values(counts).reduce((a, b) => a + b, 0);
            return (
              <Link
                key={project.id}
                to="/projects/$projectId/issues"
                params={{ projectId: project.id }}
              >
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader>
                    <CardTitle>{project.name}</CardTitle>
                    <CardDescription className="font-mono text-xs">
                      {project.path}
                    </CardDescription>
                    {project.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {project.description}
                      </p>
                    )}
                    {total > 0 && (
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {Object.entries(counts).map(([status, count]) => (
                          <span key={status} className="flex items-center gap-1 text-xs">
                            <StatusBadge status={status as IssueStatus} /> {count}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardHeader>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
