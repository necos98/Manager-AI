import { useEffect, useState } from "react";
import { RefreshCw, Database } from "lucide-react";
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
import { useUpdateProject, useCodebaseIndexStatus, useTriggerCodebaseIndex } from "@/features/projects/hooks";
import { useEvents } from "@/shared/context/event-context";
import type { WsEventData } from "@/shared/context/event-context";
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
  });

  const updateProject = useUpdateProject(project.id);
  const { data: indexStatus, refetch: refetchStatus } = useCodebaseIndexStatus(project.id);
  const triggerIndex = useTriggerCodebaseIndex(project.id);
  const [isIndexing, setIsIndexing] = useState(false);
  const events = useEvents();

  useEffect(() => {
    if (!events) return;
    return events.subscribe((event: WsEventData) => {
      if (event.project_id !== project.id) return;
      if (event.type === "embedding_started" && event.source_type === "codebase") {
        setIsIndexing(true);
      }
      if (
        (event.type === "embedding_completed" || event.type === "embedding_failed") &&
        event.source_type === "codebase"
      ) {
        setIsIndexing(false);
        refetchStatus();
      }
    });
  }, [events, project.id, refetchStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProject.mutate(
      { ...form, shell: form.shell === "__default__" ? null : form.shell },
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
          <div className="pt-2 border-t">
            <label className="text-sm font-medium flex items-center gap-1.5 mb-2">
              <Database className="size-3.5" />
              Codebase Index
            </label>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {isIndexing
                  ? "Indexing..."
                  : indexStatus?.indexed
                    ? `Indexed — ${indexStatus.file_count} file${indexStatus.file_count !== 1 ? "s" : ""}`
                    : "Not indexed"}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isIndexing || triggerIndex.isPending}
                onClick={() => {
                  setIsIndexing(true);
                  triggerIndex.mutate();
                }}
              >
                <RefreshCw className={`size-3.5 mr-1.5 ${isIndexing ? "animate-spin" : ""}`} />
                {isIndexing ? "Indexing..." : "Re-index"}
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
