import { useState } from "react";
import { ArrowDown, ArrowUp, Plus, X } from "lucide-react";
import {
  useTerminalCommands,
  useTerminalCommandVariables,
  useCreateTerminalCommand,
  useUpdateTerminalCommand,
  useReorderTerminalCommands,
  useDeleteTerminalCommand,
} from "@/features/terminals/hooks";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface TerminalCommandsEditorProps {
  projectId?: string | null;
}

export function TerminalCommandsEditor({ projectId = null }: TerminalCommandsEditorProps) {
  const { data: commands, isLoading } = useTerminalCommands(projectId);
  const { data: variables } = useTerminalCommandVariables();
  const createCommand = useCreateTerminalCommand(projectId);
  const updateCommand = useUpdateTerminalCommand(projectId);
  const reorderCommands = useReorderTerminalCommands(projectId);
  const deleteCommand = useDeleteTerminalCommand(projectId);
  const [newCmd, setNewCmd] = useState("");

  const handleAdd = () => {
    const trimmed = newCmd.trim();
    if (!trimmed) return;
    const sortOrder = commands && commands.length > 0
      ? Math.max(...commands.map((c) => c.sort_order)) + 1
      : 0;
    createCommand.mutate(
      { command: trimmed, sort_order: sortOrder, project_id: projectId },
      { onSuccess: () => setNewCmd("") },
    );
  };

  const handleBlur = (cmd: { id: number; command: string }, newValue: string) => {
    const trimmed = newValue.trim();
    if (!trimmed || trimmed === cmd.command) return;
    updateCommand.mutate({ id: cmd.id, data: { command: trimmed } });
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {commands?.length === 0 && projectId != null && (
        <p className="text-sm text-muted-foreground italic">
          No project commands configured. Global commands will be used.
        </p>
      )}

      {commands?.map((cmd, index) => (
        <div key={cmd.id} className="flex items-center gap-2">
          <div className="flex flex-col gap-0.5">
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
          <Input
            defaultValue={cmd.command}
            onBlur={(e) => handleBlur(cmd, e.target.value)}
            className="flex-1 font-mono text-sm"
          />
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive"
            onClick={() => deleteCommand.mutate(cmd.id)}
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}

      <div className="flex gap-2 mt-3">
        <Input
          value={newCmd}
          onChange={(e) => setNewCmd(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a command..."
          className="flex-1 font-mono text-sm"
        />
        <Button
          onClick={handleAdd}
          disabled={!newCmd.trim()}
          size="sm"
        >
          <Plus className="size-4 mr-1" />
          Add
        </Button>
      </div>

      {variables && variables.length > 0 && (
        <div className="mt-4 p-3 bg-muted rounded-md text-sm">
          <p className="font-medium mb-1">Available variables</p>
          <div className="space-y-0.5">
            {variables.map((v) => (
              <p key={v.name} className="text-muted-foreground">
                <code className="text-primary bg-primary/10 px-1 rounded font-mono">
                  {v.name}
                </code>{" "}
                — {v.description}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
