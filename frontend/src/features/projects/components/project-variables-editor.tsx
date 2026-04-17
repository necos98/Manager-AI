import { useState } from "react";
import { Eye, EyeOff, Plus, X } from "lucide-react";
import {
  useProjectVariables,
  useCreateProjectVariable,
  useUpdateProjectVariable,
  useDeleteProjectVariable,
} from "@/features/projects/hooks-variables";
import { revealProjectVariable } from "@/features/projects/api-variables";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { toast } from "sonner";

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
  const [revealedValues, setRevealedValues] = useState<Record<number, string>>({});

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

  const toggleReveal = async (id: number) => {
    if (id in revealedValues) {
      setRevealedValues((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      return;
    }
    try {
      const fresh = await revealProjectVariable(id);
      setRevealedValues((prev) => ({ ...prev, [id]: fresh.value }));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to reveal secret");
    }
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

      {vars?.map((v) => {
        const isRevealed = v.id in revealedValues;
        const displayValue = isRevealed
          ? revealedValues[v.id]
          : v.is_secret
            ? (v.has_value ? "••••••••" : "")
            : v.value;
        return (
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
                key={`${v.id}-${isRevealed ? "revealed" : "masked"}`}
                defaultValue={displayValue}
                disabled={v.is_secret && !isRevealed}
                onBlur={(e) => {
                  const trimmed = e.target.value.trim();
                  const baseline = isRevealed ? revealedValues[v.id] : v.value;
                  if (trimmed && trimmed !== baseline)
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
                  aria-label={isRevealed ? `Hide secret ${v.name}` : `Reveal secret ${v.name}`}
                  title={isRevealed ? "Hide value" : "Reveal value"}
                >
                  {isRevealed ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </Button>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Delete variable ${v.name}`}
              className="text-muted-foreground hover:text-destructive"
              onClick={() => deleteVar.mutate(v.id)}
            >
              <X className="size-4" />
            </Button>
          </div>
        );
      })}

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
