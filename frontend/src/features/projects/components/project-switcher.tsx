import { Check, ChevronsUpDown, FolderKanban, Plus } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { SidebarMenuButton } from "@/shared/components/ui/sidebar";
import { useProjects } from "@/features/projects/hooks";
import type { Project } from "@/shared/types";

interface ProjectSwitcherProps {
  activeProject: Project | null;
}

export function ProjectSwitcher({ activeProject }: ProjectSwitcherProps) {
  const navigate = useNavigate();
  const { data: projects } = useProjects();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton
          size="lg"
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
        >
          <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <FolderKanban className="size-4" />
          </div>
          <div className="grid flex-1 text-left text-sm leading-tight">
            <span className="truncate font-semibold">
              {activeProject?.name || "Select Project"}
            </span>
            {activeProject && (
              <span className="truncate text-xs text-muted-foreground font-mono">
                {activeProject.path}
              </span>
            )}
          </div>
          <ChevronsUpDown className="ml-auto size-4" />
        </SidebarMenuButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="w-[--radix-dropdown-menu-trigger-width] min-w-56"
        align="start"
        sideOffset={4}
      >
        {projects?.map((project) => {
          const isActive = activeProject?.id === project.id;
          return (
            <DropdownMenuItem
              key={project.id}
              onClick={() =>
                navigate({
                  to: "/projects/$projectId/issues",
                  params: { projectId: project.id },
                })
              }
              className="gap-2"
            >
              <FolderKanban className="size-4" />
              <span className="truncate flex-1">{project.name}</span>
              {isActive && <Check className="size-4 text-primary" />}
            </DropdownMenuItem>
          );
        })}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => navigate({ to: "/projects/new" })}
          className="gap-2"
        >
          <Plus className="size-4" />
          <span>New Project</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
