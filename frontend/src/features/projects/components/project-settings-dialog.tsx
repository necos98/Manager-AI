import { useEffect, useState } from "react";
import { Archive } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { useArchiveProject, useUpdateProject } from "@/features/projects/hooks";
import { useSystemInfo } from "@/features/system/hooks";
import type { Project } from "@/shared/types";

const SHELL_OPTIONS = [
  { value: "__default__", label: "Default (MANAGER_AI_SHELL env or cmd.exe)" },
  { value: "C:\\Windows\\System32\\cmd.exe", label: "cmd.exe" },
  { value: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", label: "PowerShell (Windows)" },
  { value: "C:\\Program Files\\PowerShell\\7\\pwsh.exe", label: "PowerShell 7 (pwsh)" },
  { value: "C:\\Program Files\\Git\\bin\\bash.exe", label: "Git Bash" },
  { value: "C:\\Windows\\System32\\wsl.exe", label: "WSL" },
  { value: "/bin/bash", label: "bash (Linux/macOS)" },
  { value: "/bin/zsh", label: "zsh (Linux/macOS)" },
];

interface ProjectSettingsDialogProps {
  project: Project;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProjectSettingsDialog({
  project,
  open,
  onOpenChange,
}: ProjectSettingsDialogProps) {
  const [form, setForm] = useState({
    name: project.name,
    path: project.path,
    description: project.description || "",
    tech_stack: project.tech_stack || "",
    shell: project.shell || "__default__",
    wsl_distro: project.wsl_distro || "",
  });

  // Re-sync form when the dialog opens so the newest project values are shown
  useEffect(() => {
    if (!open) return;
    setForm({
      name: project.name,
      path: project.path,
      description: project.description || "",
      tech_stack: project.tech_stack || "",
      shell: project.shell || "__default__",
      wsl_distro: project.wsl_distro || "",
    });
  }, [open, project]);

  const { data: systemInfo } = useSystemInfo();
  const isWslShell = form.shell.toLowerCase().endsWith("wsl.exe");
  const showWslUi = !!systemInfo?.wsl_available && isWslShell;

  const updateProject = useUpdateProject(project.id);
  const archiveProject = useArchiveProject();
  const navigate = useNavigate();

  const handleArchive = () => {
    const confirmed = window.confirm(
      `Archive "${project.name}"? It will be hidden from the sidebar and dashboard. You can restore it from the archived page.`,
    );
    if (!confirmed) return;
    archiveProject.mutate(project.id, {
      onSuccess: () => {
        toast.success("Project archived");
        onOpenChange(false);
        navigate({ to: "/" });
      },
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProject.mutate(
      {
        ...form,
        shell: form.shell === "__default__" ? null : form.shell,
        wsl_distro: form.wsl_distro || null,
      },
      { onSuccess: () => onOpenChange(false) }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Name</label>
            <Input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Path</label>
            <Input
              required
              value={form.path}
              onChange={(e) => setForm({ ...form, path: e.target.value })}
              className="font-mono"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Tech Stack</label>
            <Textarea
              value={form.tech_stack}
              onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Terminal Shell</label>
            <Select
              value={form.shell}
              onValueChange={(v) => setForm({ ...form, shell: v })}
            >
              <SelectTrigger className="font-mono text-sm">
                <SelectValue placeholder="Default shell" />
              </SelectTrigger>
              <SelectContent>
                {SHELL_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className="font-mono text-sm">
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              Shell to use when opening terminals for this project.
            </p>
          </div>
          {showWslUi && (
            <div>
              <label className="text-sm font-medium">WSL Distro</label>
              <Select
                value={form.wsl_distro || "__default__"}
                onValueChange={(v) =>
                  setForm({ ...form, wsl_distro: v === "__default__" ? "" : v })
                }
              >
                <SelectTrigger className="font-mono text-sm">
                  <SelectValue placeholder="Default distro" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__" className="font-mono text-sm">
                    Default distro
                  </SelectItem>
                  {systemInfo!.distros.map((d) => (
                    <SelectItem key={d} value={d} className="font-mono text-sm">
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                Claude Code must be installed inside the selected WSL distro.
              </p>
            </div>
          )}
          <div className="pt-2 border-t">
            <label className="text-sm font-medium flex items-center gap-1.5 mb-2 text-destructive">
              <Archive className="size-3.5" />
              Archive
            </label>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                Hides the project from sidebar and dashboard. You can restore it later from the archived page.
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0"
                disabled={archiveProject.isPending}
                onClick={handleArchive}
              >
                <Archive className="size-3.5 mr-1.5" />
                {archiveProject.isPending ? "Archiving..." : "Archive project"}
              </Button>
            </div>
          </div>
          {updateProject.error && (
            <p className="text-sm text-destructive">{updateProject.error.message}</p>
          )}
          <div className="flex gap-3 justify-end">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateProject.isPending}>
              {updateProject.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
