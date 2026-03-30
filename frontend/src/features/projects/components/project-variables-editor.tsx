import { useState } from "react";
import { Eye, EyeOff, Plus, X } from "lucide-react";
import {
  useProjectVariables,
  useCreateProjectVariable,
  useUpdateProjectVariable,
  useDeleteProjectVariable,
} from "@/features/projects/hooks-variables";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface ProjectVariablesEditorProps {
  projectId: string;
}

export function ProjectVariablesEditor({ projectId }: ProjectVariablesEditorProps) {
  const { data: vars, isLoading } = useProjectVariables(projectId);
  const createVar = useCreateProjectVariable(projectId);
  const updateVar = useUpdateProjectVariable(projectId);
  const deleteVar = useDeleteProjectVariable(projectId);

  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newIsSecret, setNewIsSecret] = useState(false);
  const [revealed, setRevealed] = useState<Set<number>>(new Set());

  const handleAdd = () => {
    if (!newName.trim() || !newValue.trim()) return;
    createVar.mutate(
      { name: newName.trim(), value: newValue.trim(), is_secret: newIsSecret },
      {
        onSuccess: () => {
          setNewName("");
          setNewValue("");
          setNewIsSecret(false);
        },
      }
    );
  };

  const toggleReveal = (id: number) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
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
      {vars?.length === 0 && (
        <p className="text-sm text-muted-foreground italic">No custom variables defined.</p>
      )}

      {vars?.map((v) => (
        <div key={v.id} className="flex items-center gap-2">
          <Input
            defaultValue={v.name}
            onBlur={(e) => {
              const trimmed = e.target.value.trim();
              if (trimmed && trimmed !== v.name)
                updateVar.mutate({ id: v.id, data: { name: trimmed } });
            }}
            className="w-40 font-mono text-sm"
            placeholder="NAME"
          />
          <div className="flex-1 flex gap-1">
            <Input
              defaultValue={v.value}
              type={v.is_secret && !revealed.has(v.id) ? "password" : "text"}
              onBlur={(e) => {
                const trimmed = e.target.value.trim();
                if (trimmed && trimmed !== v.value)
                  updateVar.mutate({ id: v.id, data: { value: trimmed } });
              }}
              className="flex-1 font-mono text-sm"
              placeholder="value"
            />
            {v.is_secret && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => toggleReveal(v.id)}
                title={revealed.has(v.id) ? "Hide value" : "Reveal value"}
              >
                {revealed.has(v.id) ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </Button>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive"
            onClick={() => deleteVar.mutate(v.id)}
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}

      <div className="flex gap-2 mt-4 pt-4 border-t">
        <Input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="NAME"
          className="w-40 font-mono text-sm"
        />
        <Input
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          type={newIsSecret ? "password" : "text"}
          placeholder="value"
          className="flex-1 font-mono text-sm"
        />
        <label className="flex items-center gap-1.5 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={newIsSecret}
            onChange={(e) => setNewIsSecret(e.target.checked)}
            className="rounded"
          />
          Secret
        </label>
        <Button
          onClick={handleAdd}
          disabled={!newName.trim() || !newValue.trim() || createVar.isPending}
          size="sm"
        >
          <Plus className="size-4 mr-1" />
          Add
        </Button>
      </div>
      {createVar.error && (
        <p className="text-sm text-destructive">{createVar.error.message}</p>
      )}
    </div>
  );
}
