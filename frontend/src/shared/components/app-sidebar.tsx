import {
  Activity,
  BookOpen,
  Brain,
  CircleDot,
  FileText,
  HeartPulse,
  Key,
  LayoutDashboard,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Settings,
  Smartphone,
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
import { SmartphoneQrDialog } from "@/shared/components/smartphone-qr-dialog";
import { useTerminalCount } from "@/features/terminals/hooks";
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
  const [smartphoneQrOpen, setSmartphoneQrOpen] = useState(false);

  const projectId = activeProject?.id;

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
          label: "Variables",
          to: "/projects/$projectId/variables" as const,
          params: { projectId },
          icon: Key,
        },
        {
          label: "Activity",
          to: "/projects/$projectId/activity" as const,
          params: { projectId },
          icon: Activity,
        },
        {
          label: "Memories",
          to: "/projects/$projectId/memories" as const,
          params: { projectId },
          icon: Brain,
        },
        {
          label: "Ask & Brainstorming",
          to: "/projects/$projectId/ask" as const,
          params: { projectId },
          icon: MessageSquare,
        },
        {
          label: "Library",
          to: "/projects/$projectId/library" as const,
          params: { projectId },
          icon: BookOpen,
        },
        {
          label: "Health",
          to: "/projects/$projectId/health" as const,
          params: { projectId },
          icon: HeartPulse,
        },
      ]
    : [];

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
                    isActive={!!matchRoute({ to: "/dashboard", fuzzy: true })}
                  >
                    <Link to="/dashboard">
                      <LayoutDashboard />
                      <span>Dashboard</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
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
                    isActive={!!matchRoute({ to: "/library", fuzzy: true })}
                  >
                    <Link to="/library">
                      <BookOpen />
                      <span>Library</span>
                    </Link>
                  </SidebarMenuButton>
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
              <SidebarMenuButton size="sm" onClick={() => setSmartphoneQrOpen(true)}>
                <Smartphone className="h-4 w-4" />
                <span className="text-xs">Show on Smartphone</span>
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

      <SmartphoneQrDialog
        open={smartphoneQrOpen}
        onOpenChange={setSmartphoneQrOpen}
      />
    </>
  );
}
