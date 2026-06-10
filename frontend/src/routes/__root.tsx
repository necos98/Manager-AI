import { createRootRoute, Outlet, useLocation, useNavigate } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { ThemeProvider, useTheme } from "next-themes";
import { useState, useCallback } from "react";
import { queryClient } from "@/shared/lib/query-client";
import { SidebarProvider, SidebarTrigger } from "@/shared/components/ui/sidebar";
import { AppSidebar } from "@/shared/components/app-sidebar";
import { ProjectSidebar } from "@/shared/components/project-sidebar";
import { EventProvider } from "@/shared/context/event-context";
import { ErrorBoundary } from "@/shared/components/error-boundary";
import { CommandPalette } from "@/features/command-palette/components/command-palette";
import { PageBreadcrumb } from "@/shared/components/page-breadcrumb";
import { useKeyboardShortcuts } from "@/shared/hooks/use-keyboard-shortcuts";
import { useProject } from "@/features/projects/hooks";
import { TerminalProvider } from "@/features/terminals/contexts/terminal-context";
import { useGlobalImagePaste } from "@/features/terminals/hooks/use-global-image-paste";
import { Button } from "@/shared/components/ui/button";
import { PanelLeft } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/shared/components/ui/sheet";

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

  // Per-sidebar collapse state with localStorage persistence
  const [projectSidebarOpen, setProjectSidebarOpen] = useState(() => {
    const stored = localStorage.getItem("sidebar-project");
    return stored !== null ? stored === "true" : true;
  });

  const [appSidebarOpen, setAppSidebarOpen] = useState(() => {
    const stored = localStorage.getItem("sidebar-app");
    return stored !== null ? stored === "true" : true;
  });

  const handleProjectSidebarChange = useCallback((open: boolean) => {
    setProjectSidebarOpen(open);
    localStorage.setItem("sidebar-project", String(open));
  }, []);

  // ── Command palette + keyboard shortcuts ──
  const navigate = useNavigate();
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);

  const shortcutCallbacks = {
    onCmdPalette: useCallback(() => setCmdPaletteOpen((prev) => !prev), []),
    onNewIssue: useCallback(() => {
      if (projectId) {
        navigate({ to: "/projects/$projectId/issues", params: { projectId } });
        // The NewIssueDialog on the issues page will need to be triggered — for now open the issues page
      }
    }, [navigate, projectId]),
    onNavigate: useCallback(
      (path: string) => {
        if (path === "/issues" && projectId) {
          navigate({ to: "/projects/$projectId/issues", params: { projectId } });
        } else if (path === "/") {
          navigate({ to: "/" });
        } else if (path === "/projects") {
          navigate({ to: "/" });
        }
      },
      [navigate, projectId],
    ),
    onSearchFocus: useCallback(() => {
      // Try to focus the first search input on the page
      const searchInput = document.querySelector<HTMLInputElement>('input[type="search"], input[placeholder*="search" i]');
      searchInput?.focus();
    }, []),
    onHelp: useCallback(() => {
      setCmdPaletteOpen(true);
    }, []),
  };

  useKeyboardShortcuts(shortcutCallbacks);

  const handleAppSidebarChange = useCallback((open: boolean) => {
    setAppSidebarOpen(open);
    localStorage.setItem("sidebar-app", String(open));
  }, []);

  return (
    <div className="flex min-h-svh w-full">
      <div className="flex shrink-0">
        {/* ProjectSidebar with its own SidebarProvider for independent collapse */}
        <SidebarProvider
          style={{ "--sidebar-width": "220px" } as React.CSSProperties}
          open={projectSidebarOpen}
          onOpenChange={handleProjectSidebarChange}
        >
          <ProjectSidebar activeProject={activeProject} />
        </SidebarProvider>

        {/* AppSidebar with its own SidebarProvider for independent collapse */}
        {activeProject && (
          <SidebarProvider
            style={{ "--sidebar-width": "260px" } as React.CSSProperties}
            open={appSidebarOpen}
            onOpenChange={handleAppSidebarChange}
          >
            <AppSidebar
              activeProject={activeProject}
              className={projectSidebarOpen ? "left-[220px]" : "left-[3rem]"}
            />
          </SidebarProvider>
        )}
      </div>

      {/* Main content area */}
      <div className="min-w-0 flex flex-1 flex-col main-content-gradient">
        {/* Mobile header: Sheet-based trigger for ProjectSidebar */}
        <header className="md:hidden flex h-12 items-center px-4 border-b bg-background shrink-0">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open sidebar">
                <PanelLeft className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[220px] p-0">
              <SidebarProvider
                style={{ "--sidebar-width": "220px" } as React.CSSProperties}
                open={projectSidebarOpen}
                onOpenChange={handleProjectSidebarChange}
              >
                <ProjectSidebar activeProject={activeProject} />
              </SidebarProvider>
            </SheetContent>
          </Sheet>
        </header>
        <PageBreadcrumb />
        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <CommandPalette open={cmdPaletteOpen} onOpenChange={setCmdPaletteOpen} />
    </div>
  );
}

export const Route = createRootRoute({
  component: RootComponent,
});
