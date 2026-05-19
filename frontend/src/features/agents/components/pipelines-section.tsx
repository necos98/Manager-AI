import { useState } from "react";
import { Plus, Pencil, Trash2, Star } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import {
  useAgents,
  usePipelines,
  useCreatePipeline,
  useUpdatePipeline,
  useDeletePipeline,
} from "../hooks";
import type { PipelineData, PipelineStepData } from "../api";

interface PipelinesSectionProps {
  projectId: string;
}

export function PipelinesSection({ projectId }: PipelinesSectionProps) {
  const { data: agents } = useAgents(projectId);
  const { data: pipelinesData, isLoading } = usePipelines(projectId);
  const createPipeline = useCreatePipeline(projectId);
  const updatePipeline = useUpdatePipeline(projectId);
  const deletePipeline = useDeletePipeline(projectId);

  const pipelines = pipelinesData?.pipelines ?? [];

  const [editing, setEditing] = useState<PipelineData | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", steps: [] as PipelineStepData[], is_default: false });

  function openEdit(p: PipelineData) {
    setEditing(p);
    setForm({ name: p.name, steps: [...p.steps], is_default: p.is_default });
  }

  function openAdd() {
    setAdding(true);
    setForm({ name: "", steps: [], is_default: false });
  }

  function handleSave() {
    if (!editing) return;
    updatePipeline.mutate({
      pipelineId: editing.id,
      data: { name: form.name, steps: form.steps, is_default: form.is_default },
    }, { onSuccess: () => setEditing(null) });
  }

  function handleCreate() {
    createPipeline.mutate(
      { name: form.name, steps: form.steps, is_default: form.is_default },
      { onSuccess: () => setAdding(false) }
    );
  }

  function addStep(agentId: string) {
    if (!agentId) return;
    const maxOrder = form.steps.reduce((max, s) => Math.max(max, s.order), -1);
    setForm({
      ...form,
      steps: [...form.steps, { agent_id: agentId, order: maxOrder + 1 }],
    });
  }

  function removeStep(index: number) {
    const newSteps = form.steps
      .filter((_, i) => i !== index)
      .map((s, i) => ({ ...s, order: i }));
    setForm({ ...form, steps: newSteps });
  }

  function moveStep(index: number, direction: -1 | 1) {
    const newSteps = [...form.steps];
    const target = index + direction;
    if (target < 0 || target >= newSteps.length) return;
    [newSteps[index], newSteps[target]] = [newSteps[target], newSteps[index]];
    newSteps.forEach((s, i) => (s.order = i));
    setForm({ ...form, steps: newSteps });
  }

  function getAgentName(agentId: string): string {
    return agents?.find((a) => a.id === agentId)?.name ?? agentId.slice(0, 8);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Pipelines</label>
        <Button type="button" variant="outline" size="sm" onClick={openAdd}>
          <Plus className="size-3.5 mr-1" />
          Add Pipeline
        </Button>
      </div>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading...</p>
      ) : pipelines.length > 0 ? (
        <div className="space-y-1">
          {pipelines.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div className="flex items-center gap-2 min-w-0">
                {p.is_default && <Star className="size-3.5 text-amber-500 fill-amber-500 shrink-0" />}
                <span className="font-medium">{p.name}</span>
                <span className="text-xs text-muted-foreground">
                  {p.steps.length} step{p.steps.length !== 1 ? "s" : ""}
                </span>
                <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{p.trigger_type}</span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(p)}>
                  <Pencil className="size-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  disabled={deletePipeline.isPending}
                  onClick={() => deletePipeline.mutate(p.id)}
                >
                  <Trash2 className="size-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No pipelines defined yet.</p>
      )}

      {/* Add/Edit Pipeline Dialog */}
      <Dialog
        open={adding || !!editing}
        onOpenChange={(open) => {
          if (!open) {
            setAdding(false);
            setEditing(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Pipeline" : "New Pipeline"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Default" />
            </div>

            <div>
              <label className="text-sm font-medium">Steps</label>
              <div className="space-y-1 mt-1">
                {form.steps.map((step, i) => (
                  <div key={i} className="flex items-center gap-2 rounded border px-2 py-1 text-sm">
                    <span className="text-xs text-muted-foreground w-5">{i + 1}.</span>
                    <span className="flex-1">{getAgentName(step.agent_id)}</span>
                    <Button type="button" variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => moveStep(i, -1)} disabled={i === 0}>
                      ↑
                    </Button>
                    <Button type="button" variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => moveStep(i, 1)} disabled={i === form.steps.length - 1}>
                      ↓
                    </Button>
                    <Button type="button" variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive" onClick={() => removeStep(i)}>
                      <Trash2 className="size-3" />
                    </Button>
                  </div>
                ))}
              </div>
              {agents && agents.length > 0 && (
                <div className="flex gap-2 mt-2">
                  <select
                    className="flex-1 text-sm border rounded px-2 py-1 bg-background"
                    onChange={(e) => { addStep(e.target.value); e.target.value = ""; }}
                    defaultValue=""
                  >
                    <option value="" disabled>Add agent...</option>
                    {agents.filter((a) => a.enabled).map((a) => (
                      <option key={a.id} value={a.id}>{a.name} ({a.role_key})</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is-default"
                checked={form.is_default}
                onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
              />
              <label htmlFor="is-default" className="text-sm">Set as default pipeline</label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setAdding(false); setEditing(null); }}>
              Cancel
            </Button>
            <Button
              onClick={editing ? handleSave : handleCreate}
              disabled={createPipeline.isPending || updatePipeline.isPending}
            >
              {editing
                ? updatePipeline.isPending ? "Saving..." : "Save"
                : createPipeline.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
