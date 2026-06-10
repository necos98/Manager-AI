import {
  Bot,
  Cable,
  HelpCircle,
  LayoutDashboard,
  ListOrdered,
  Plus,
  Settings,
  Smartphone,
  Star,
  Terminal,
  Workflow,
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
  SidebarMenuAction,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from "@/shared/components/ui/sidebar";
import { SmartphoneQrDialog } from "@/shared/components/smartphone-qr-dialog";
import { ThemeToggle } from "@/shared/components/theme-toggle";
import { useProjects, useUpdateProject } from "@/features/projects/hooks";
import { useTerminalCount } from "@/features/terminals/hooks";
import { usePendingCount } from "@/features/questions/hooks";
import type { Project } from "@/shared/types";
import { QuickCreateIssueDialog } from "@/features/issues/components/quick-create-issue-dialog";

interface ProjectSidebarProps {
  activeProject: Project | null;
}

function ProjectSidebarItem({
  project,
  isActive,
  onQuickCreate,
}: {
  project: Project;
  isActive: boolean;
  onQuickCreate: () => void;
}) {
  const updateProject = useUpdateProject(project.id);
  const isFavorited = !!project.favorited_at;

  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={isActive} tooltip={project.name}>
        <Link to="/projects/$projectId/issues" params={{ projectId: project.id }}>
          <span>{project.name}</span>
        </Link>
      </SidebarMenuButton>
      <SidebarMenuAction
        onClick={() =>
          updateProject.mutate({
            favorited_at: isFavorited ? null : new Date().toISOString(),
          })
        }
      >
        <Star
          className={isFavorited ? "text-yellow-400" : ""}
          fill={isFavorited ? "currentColor" : "none"}
        />
      </SidebarMenuAction>
      <SidebarMenuAction onClick={onQuickCreate} tooltip="Quick create issue">
        <Plus />
      </SidebarMenuAction>
    </SidebarMenuItem>
  );
}

export function ProjectSidebar({ activeProject }: ProjectSidebarProps) {
  const { data: projects } = useProjects(false);
  const { data: countData } = useTerminalCount();
  const terminalCount = countData?.count ?? 0;
  const { data: pendingQuestionsCount } = usePendingCount();
  const questionsPendingCount = pendingQuestionsCount?.count ?? 0;
  const matchRoute = useMatchRoute();

  const [smartphoneQrOpen, setSmartphoneQrOpen] = useState(false);
  const [quickCreateProjectId, setQuickCreateProjectId] = useState<string | null>(null);

  return (
    <>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center gap-2 px-2 py-1">
                <span className="font-semibold text-sm">Manager AI</span>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Projects</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {projects?.map((project) => {
                  const isActive =
                    activeProject?.id === project.id &&
                    !!matchRoute({ to: "/projects/$projectId", params: { projectId: project.id }, fuzzy: true });
                  return (
                    <ProjectSidebarItem
                      key={project.id}
                      project={project}
                      isActive={isActive}
                      onQuickCreate={() => setQuickCreateProjectId(project.id)}
                    />
                  );
                })}
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/projects/new", fuzzy: true })}
                    tooltip="New Project"
                  >
                    <Link to="/projects/new">
                      <span className="text-muted-foreground">+ New Project</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator />

          <SidebarGroup>
            <SidebarGroupLabel>Global</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/dashboard", fuzzy: true })}
                    tooltip="Dashboard"
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
                    isActive={!!matchRoute({ to: "/queue", fuzzy: true })}
                    tooltip="Queue"
                  >
                    <Link to="/queue">
                      <ListOrdered />
                      <span>Queue</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/terminals", fuzzy: true })}
                    tooltip="Terminals"
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
                    isActive={!!matchRoute({ to: "/agents", fuzzy: true })}
                    tooltip="Agents"
                  >
                    <Link to="/agents">
                      <Bot />
                      <span>Agents</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/providers", fuzzy: true })}
                    tooltip="Provider"
                  >
                    <Link to="/providers">
                      <Cable />
                      <span>Provider</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/questions", fuzzy: true })}
                    tooltip="Questions"
                  >
                    <Link to="/questions">
                      <HelpCircle />
                      <span>Questions</span>
                    </Link>
                  </SidebarMenuButton>
                  {questionsPendingCount > 0 && (
                    <SidebarMenuBadge>{questionsPendingCount}</SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/pipelines", fuzzy: true })}
                    tooltip="Pipelines"
                  >
                    <Link to="/pipelines">
                      <Workflow />
                      <span>Pipelines</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={!!matchRoute({ to: "/settings", fuzzy: true })}
                    tooltip="Settings"
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
              <SidebarMenuButton size="sm" onClick={() => setSmartphoneQrOpen(true)} tooltip="Show on Smartphone">
                <Smartphone className="h-4 w-4" />
                <span className="text-xs">Show on Smartphone</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <ThemeToggle />
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>

        <SidebarRail />
      </Sidebar>

      <SmartphoneQrDialog
        open={smartphoneQrOpen}
        onOpenChange={setSmartphoneQrOpen}
      />

      <QuickCreateIssueDialog
        projectId={quickCreateProjectId ?? ""}
        open={quickCreateProjectId !== null}
        onOpenChange={(open) => {
          if (!open) setQuickCreateProjectId(null);
        }}
      />
    </>
  );
}
