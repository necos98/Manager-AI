import { useState } from "react";
import { ArrowDown, ArrowUp, ChevronDown, Plus, X } from "lucide-react";
import {
  useTerminalCommands,
  useTerminalCommandVariables,
  useTerminalCommandTemplates,
  useCreateTerminalCommand,
  useUpdateTerminalCommand,
  useReorderTerminalCommands,
  useDeleteTerminalCommand,
} from "@/features/terminals/hooks";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface TerminalCommandsEditorProps {
  projectId?: string | null;
}

export function TerminalCommandsEditor({ projectId = null }: TerminalCommandsEditorProps) {
  const { data: commands, isLoading } = useTerminalCommands(projectId);
  const { data: variables } = useTerminalCommandVariables();
  const { data: templates } = useTerminalCommandTemplates();
  const createCommand = useCreateTerminalCommand(projectId);
  const updateCommand = useUpdateTerminalCommand(projectId);
  const reorderCommands = useReorderTerminalCommands(projectId);
  const deleteCommand = useDeleteTerminalCommand(projectId);

  const [newCmd, setNewCmd] = useState("");
  const [newCondition, setNewCondition] = useState("");

  const handleAdd = (command?: string) => {
    const trimmed = (command ?? newCmd).trim();
    if (!trimmed) return;
    const sortOrder =
      commands && commands.length > 0
        ? Math.max(...commands.map((c) => c.sort_order)) + 1
        : 0;
    createCommand.mutate(
      {
        command: trimmed,
        sort_order: sortOrder,
        project_id: projectId,
        condition: newCondition.trim() || undefined,
      },
      {
        onSuccess: () => {
          setNewCmd("");
          setNewCondition("");
        },
      }
    );
  };

  const handleBlurCommand = (cmd: { id: number; command: string }, newValue: string) => {
    if (newValue === cmd.command) return;
    if (!newValue.trim()) return;
    updateCommand.mutate({ id: cmd.id, data: { command: newValue } });
  };

  const handleBlurCondition = (cmd: { id: number; condition?: string | null }, newValue: string) => {
    const trimmed = newValue.trim() || null;
    if (trimmed === (cmd.condition ?? null)) return;
    updateCommand.mutate({ id: cmd.id, data: { condition: trimmed ?? undefined } });
  };

  const handleMove = (index: number, direction: number) => {
    if (!commands) return;
    const swapIndex = index + direction;
    if (swapIndex < 0 || swapIndex >= commands.length) return;
    reorderCommands.mutate([
      { id: commands[index].id, sort_order: commands[swapIndex].sort_order },
      { id: commands[swapIndex].id, sort_order: commands[index].sort_order },
    ]);
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => <Skeleton key={i} className="h-10" />)}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {commands?.length === 0 && projectId != null && (
        <p className="text-sm text-muted-foreground italic">
          No project commands configured. Global commands will be used.
        </p>
      )}

      {commands?.map((cmd, index) => (
        <div key={cmd.id} className="flex gap-2 items-start">
          <div className="flex flex-col gap-0.5 pt-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={() => handleMove(index, -1)}
              disabled={index === 0}
            >
              <ArrowUp className="size-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={() => handleMove(index, 1)}
              disabled={index === (commands?.length ?? 0) - 1}
            >
              <ArrowDown className="size-3" />
            </Button>
          </div>
          <div className="flex-1 space-y-1">
            <Textarea
              defaultValue={cmd.command}
              onBlur={(e) => handleBlurCommand(cmd, e.target.value)}
              className="font-mono text-sm min-h-[60px] resize-y"
              placeholder="Command (multi-line supported)"
            />
            <Input
              defaultValue={cmd.condition ?? ""}
              onBlur={(e) => handleBlurCondition(cmd, e.target.value)}
              className="text-xs font-mono h-7"
              placeholder="Condition (e.g. $issue_status == ACCEPTED)"
            />
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive mt-1"
            onClick={() => deleteCommand.mutate(cmd.id)}
          >
            <X className="size-3" />
          </Button>
        </div>
      ))}

      {/* Add new command */}
      <div className="border-t pt-3 space-y-2">
        <div className="flex gap-2 items-start">
          <Textarea
            value={newCmd}
            onChange={(e) => setNewCmd(e.target.value)}
            className="font-mono text-sm min-h-[60px] resize-y flex-1"
            placeholder="New command (multi-line supported)"
          />
          <div className="flex flex-col gap-1">
            <Button
              size="sm"
              onClick={() => handleAdd()}
              disabled={!newCmd.trim() || createCommand.isPending}
              className="h-7"
            >
              <Plus className="size-3 mr-1" />
              Add
            </Button>
            {templates && templates.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="h-7">
                    <ChevronDown className="size-3 mr-1" />
                    Templates
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {templates.map((t) => (
                    <DropdownMenuItem key={t.name} onClick={() => handleAdd(t.command)}>
                      {t.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
        <Input
          value={newCondition}
          onChange={(e) => setNewCondition(e.target.value)}
          className="text-xs font-mono h-7"
          placeholder="Condition (optional, e.g. $issue_status == ACCEPTED)"
        />
      </div>

      {/* Variable reference */}
      {variables && variables.length > 0 && (
        <div className="text-xs text-muted-foreground">
          <span className="font-medium">Variables:</span>{" "}
          {variables.map((v) => v.name).join(", ")}
        </div>
      )}
    </div>
  );
}
