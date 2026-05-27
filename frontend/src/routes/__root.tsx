import { createRootRoute, Outlet, useLocation } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { ThemeProvider, useTheme } from "next-themes";
import { queryClient } from "@/shared/lib/query-client";
import { SidebarProvider, SidebarTrigger } from "@/shared/components/ui/sidebar";
import { AppSidebar } from "@/shared/components/app-sidebar";
import { ProjectSidebar } from "@/shared/components/project-sidebar";
import { EventProvider } from "@/shared/context/event-context";
import { ErrorBoundary } from "@/shared/components/error-boundary";
import { useProject } from "@/features/projects/hooks";
import { TerminalProvider } from "@/features/terminals/contexts/terminal-context";
import { useGlobalImagePaste } from "@/features/terminals/hooks/use-global-image-paste";

function GlobalPasteBridge() {
  useGlobalImagePaste();
  return null;
}

function ThemeToaster() {
  const { theme } = useTheme();
  return (
    <Toaster
      position="bottom-right"
      richColors
      closeButton
      theme={theme as "light" | "dark" | "system" | undefined}
    />
  );
}

function RootComponent() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <TerminalProvider>
          <GlobalPasteBridge />
          <EventProvider>
            <RootLayout />
            <ThemeToaster />
          </EventProvider>
        </TerminalProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

function RootLayout() {
  const { pathname } = useLocation();
  const projectId = pathname.match(/\/projects\/([^/]+)/)?.[1] ?? null;
  const projectQuery = useProject(projectId ?? "");
  const activeProject = projectId ? (projectQuery.data ?? null) : null;

  return (
    <SidebarProvider
      style={{ "--sidebar-width": "220px" } as React.CSSProperties}
    >
      <div className="flex min-h-svh w-full">
        {/* Left column: the two sidebars stacked side-by-side */}
        <div className="flex shrink-0">
          <ProjectSidebar activeProject={activeProject} />
          {activeProject && <AppSidebar activeProject={activeProject} className="left-(--sidebar-width)" />}
        </div>

        {/* Main content area */}
        <div className="min-w-0 flex flex-1 flex-col">
          <header className="md:hidden flex h-12 items-center px-4 border-b bg-background shrink-0">
            <SidebarTrigger />
          </header>
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}

export const Route = createRootRoute({
  component: RootComponent,
});
