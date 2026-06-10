import {
  Activity,
  Brain,
  CircleDot,
  FileText,
  HeartPulse,
  MessageSquare,
  Pencil,
  Plug,
  Settings,
} from "lucide-react";
import { useState } from "react";
import { Link, useMatchRoute } from "@tanstack/react-router";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/shared/components/ui/sidebar";
import { ProjectSettingsDialog } from "@/features/projects/components/project-settings-dialog";
import { McpSetupDialog } from "@/features/projects/components/mcp-setup-dialog";
import type { Project } from "@/shared/types";

interface AppSidebarProps {
  activeProject: Project | null;
  className?: string;
}

export function AppSidebar({ activeProject, className }: AppSidebarProps) {
  const matchRoute = useMatchRoute();

  const [projectSettingsOpen, setProjectSettingsOpen] = useState(false);
  const [mcpSetupOpen, setMcpSetupOpen] = useState(false);

  if (!activeProject) return null;

  const projectId = activeProject.id;

  const projectNav = [
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
      label: "Health",
      to: "/projects/$projectId/health" as const,
      params: { projectId },
      icon: HeartPulse,
    },
  ];

  return (
    <>
      <Sidebar collapsible="icon" className={className}>
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center gap-2 px-2 py-1">
                <span className="font-semibold text-sm truncate">{activeProject.name}</span>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Project</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {projectNav.map((item) => (
                  <SidebarMenuItem key={item.label}>
                    <SidebarMenuButton
                      asChild
                      isActive={!!matchRoute({ to: item.to, params: item.params, fuzzy: true })}
                      tooltip={item.label}
                    >
                      <Link to={item.to} params={item.params}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => setProjectSettingsOpen(true)} tooltip="Edit Project">
                    <Pencil />
                    <span>Edit Project</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/projects/$projectId/plugins", params: { projectId }, fuzzy: true })}
                    tooltip="MCP Plugins"
                  >
                    <Link to="/projects/$projectId/plugins" params={{ projectId }}>
                      <Plug />
                      <span>MCP Plugins</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => setMcpSetupOpen(true)} tooltip="MCP Setup">
                    <Settings />
                    <span>MCP Setup</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarRail />
      </Sidebar>

      <ProjectSettingsDialog
        project={activeProject}
        open={projectSettingsOpen}
        onOpenChange={setProjectSettingsOpen}
      />

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
