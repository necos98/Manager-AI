import {
  Activity,
  CircleDot,
  Download,
  FileText,
  FolderSync,
  MoreHorizontal,
  Pencil,
  Plug,
  Settings,
  SquareTerminal,
  Terminal,
} from "lucide-react";
import { useState } from "react";
import { Link, useMatchRoute } from "@tanstack/react-router";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/shared/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { ProjectSwitcher } from "@/features/projects/components/project-switcher";
import { ProjectSettingsDialog } from "@/features/projects/components/project-settings-dialog";
import { McpSetupDialog } from "@/features/projects/components/mcp-setup-dialog";
import { useInstallManagerJson, useInstallClaudeResources } from "@/features/projects/hooks";
import { useTerminalCount } from "@/features/terminals/hooks";
import { toast } from "sonner";
import type { Project } from "@/shared/types";

interface AppSidebarProps {
  activeProject: Project | null;
}

export function AppSidebar({ activeProject }: AppSidebarProps) {
  const { data: countData } = useTerminalCount();
  const terminalCount = countData?.count ?? 0;
  const matchRoute = useMatchRoute();

  const [projectSettingsOpen, setProjectSettingsOpen] = useState(false);
  const [mcpSetupOpen, setMcpSetupOpen] = useState(false);

  const projectId = activeProject?.id;

  const installManagerJson = useInstallManagerJson(projectId ?? "");
  const installClaudeResources = useInstallClaudeResources(projectId ?? "");

  const projectNav = projectId
    ? [
        {
          label: "Issues",
          to: "/projects/$projectId/issues" as const,
          params: { projectId },
          icon: CircleDot,
        },
        {
          label: "Files",
          to: "/projects/$projectId/files" as const,
          params: { projectId },
          icon: FileText,
        },
        {
          label: "Commands",
          to: "/projects/$projectId/commands" as const,
          params: { projectId },
          icon: SquareTerminal,
        },
        {
          label: "Activity",
          to: "/projects/$projectId/activity" as const,
          params: { projectId },
          icon: Activity,
        },
      ]
    : [];

  function handleInstallManagerJson() {
    installManagerJson.mutate(undefined, {
      onSuccess: () => toast.success("manager.json installed successfully"),
      onError: (err) => toast.error(`Failed to install manager.json: ${err.message}`),
    });
  }

  function handleInstallClaudeResources() {
    installClaudeResources.mutate(undefined, {
      onSuccess: () => toast.success("Claude resources installed successfully"),
      onError: (err) => toast.error(`Failed to install Claude resources: ${err.message}`),
    });
  }

  function handleExportManagerJson() {
    if (projectId) {
      window.open(`/api/projects/${projectId}/export-manager-json`);
    }
  }

  return (
    <>
      <Sidebar>
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <ProjectSwitcher activeProject={activeProject} />
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          {projectId && (
            <SidebarGroup>
              <SidebarGroupLabel>Project</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {projectNav.map((item) => (
                    <SidebarMenuItem key={item.label}>
                      <SidebarMenuButton
                        asChild
                        isActive={!!matchRoute({ to: item.to, params: item.params, fuzzy: true })}
                      >
                        <Link to={item.to} params={item.params}>
                          <item.icon />
                          <span>{item.label}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                  <SidebarMenuItem>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuButton>
                          <MoreHorizontal />
                          <span>More</span>
                        </SidebarMenuButton>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent side="right" align="start">
                        <DropdownMenuItem onClick={() => setProjectSettingsOpen(true)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit Project
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={handleInstallManagerJson}>
                          <FolderSync className="mr-2 h-4 w-4" />
                          Install manager.json
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={handleInstallClaudeResources}>
                          <Plug className="mr-2 h-4 w-4" />
                          Install Claude Resources
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={handleExportManagerJson}>
                          <Download className="mr-2 h-4 w-4" />
                          Export manager.json
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => setMcpSetupOpen(true)}>
                          <Settings className="mr-2 h-4 w-4" />
                          MCP Setup
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )}

          <SidebarSeparator />

          <SidebarGroup>
            <SidebarGroupLabel>Global</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/terminals", fuzzy: true })}
                  >
                    <Link to="/terminals">
                      <Terminal />
                      <span>Terminals</span>
                    </Link>
                  </SidebarMenuButton>
                  {terminalCount > 0 && (
                    <SidebarMenuBadge>{terminalCount}</SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/settings", fuzzy: true })}
                  >
                    <Link to="/settings">
                      <Settings />
                      <span>Settings</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild size="sm">
                <span className="text-xs text-muted-foreground">Manager AI</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>

      {activeProject && (
        <ProjectSettingsDialog
          project={activeProject}
          open={projectSettingsOpen}
          onOpenChange={setProjectSettingsOpen}
        />
      )}

      {projectId && (
        <McpSetupDialog
          projectId={projectId}
          open={mcpSetupOpen}
          onOpenChange={setMcpSetupOpen}
        />
      )}
    </>
  );
}
