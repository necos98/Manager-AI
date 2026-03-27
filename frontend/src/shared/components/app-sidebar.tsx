import {
  CircleDot,
  FileText,
  Settings,
  SquareTerminal,
  Terminal,
} from "lucide-react";
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
import { ProjectSwitcher } from "@/features/projects/components/project-switcher";
import { useTerminalCount } from "@/features/terminals/hooks";
import type { Project } from "@/shared/types";

interface AppSidebarProps {
  activeProject: Project | null;
}

export function AppSidebar({ activeProject }: AppSidebarProps) {
  const { data: countData } = useTerminalCount();
  const terminalCount = countData?.count ?? 0;
  const matchRoute = useMatchRoute();

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
      ]
    : [];

  return (
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
  );
}
