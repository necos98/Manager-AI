import { createRootRoute, Outlet } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { queryClient } from "@/shared/lib/query-client";
import { SidebarInset, SidebarProvider } from "@/shared/components/ui/sidebar";
import { AppSidebar } from "@/shared/components/app-sidebar";
import { EventProvider } from "@/shared/context/event-context";
import { useProject } from "@/features/projects/hooks";

function RootComponent() {
  return (
    <QueryClientProvider client={queryClient}>
      <EventProvider>
        <RootLayout />
        <Toaster position="bottom-right" richColors closeButton />
      </EventProvider>
    </QueryClientProvider>
  );
}

function RootLayout() {
  const projectId = extractProjectIdFromUrl();
  const projectQuery = useProject(projectId ?? "");
  const activeProject = projectId ? (projectQuery.data ?? null) : null;

  return (
    <SidebarProvider>
      <AppSidebar activeProject={activeProject} />
      <SidebarInset>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

function extractProjectIdFromUrl(): string | null {
  const match = window.location.pathname.match(/\/projects\/([^/]+)/);
  return match?.[1] ?? null;
}

export const Route = createRootRoute({
  component: RootComponent,
});
