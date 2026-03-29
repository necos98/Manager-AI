import { createRootRoute, Outlet, useLocation } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { queryClient } from "@/shared/lib/query-client";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/shared/components/ui/sidebar";
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
  const { pathname } = useLocation();
  const projectId = pathname.match(/\/projects\/([^/]+)/)?.[1] ?? null;
  const projectQuery = useProject(projectId ?? "");
  const activeProject = projectId ? (projectQuery.data ?? null) : null;

  return (
    <SidebarProvider>
      <AppSidebar activeProject={activeProject} />
      <SidebarInset className="min-w-0 flex flex-col">
        <header className="md:hidden flex h-12 items-center px-4 border-b bg-background shrink-0">
          <SidebarTrigger />
        </header>
        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

export const Route = createRootRoute({
  component: RootComponent,
});
