import { createFileRoute, Link } from "@tanstack/react-router";
import { useDashboard } from "@/features/projects/hooks-dashboard";
import { StatusBadge } from "@/features/issues/components/status-badge";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
});

function DashboardPage() {
  const { data: projects, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2].map((i) => <Skeleton key={i} className="h-32" />)}
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-6">Dashboard</h1>
      {!projects || projects.length === 0 ? (
        <p className="text-muted-foreground">Nessun progetto ancora.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((project) => (
            <Card key={project.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  <Link
                    to="/projects/$projectId/issues"
                    params={{ projectId: project.id }}
                    className="hover:underline"
                  >
                    {project.name}
                  </Link>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {project.active_issues.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nessuna issue attiva</p>
                ) : (
                  <ul className="space-y-1.5">
                    {project.active_issues.map((issue) => (
                      <li key={issue.id}>
                        <Link
                          to="/projects/$projectId/issues/$issueId"
                          params={{ projectId: project.id, issueId: issue.id }}
                          className="flex items-center gap-2 text-sm hover:underline"
                        >
                          <StatusBadge status={issue.status} />
                          <span className="truncate flex-1">
                            {issue.name || issue.description}
                          </span>
                          <span className="text-xs text-muted-foreground flex-shrink-0">P{issue.priority}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
