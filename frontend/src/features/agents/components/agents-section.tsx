import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { useAgents, useCreateAgent, useUpdateAgent, useDeleteAgent } from "../hooks";
import type { AgentData } from "../api";

interface AgentsSectionProps {
  projectId: string;
}

export function AgentsSection({ projectId }: AgentsSectionProps) {
  const { data: agents, isLoading } = useAgents(projectId);
  const createAgent = useCreateAgent(projectId);
  const updateAgent = useUpdateAgent(projectId);
  const deleteAgent = useDeleteAgent(projectId);

  const [editing, setEditing] = useState<AgentData | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", role_key: "", system_prompt: "" });

  function openEdit(agent: AgentData) {
    setEditing(agent);
    setForm({ name: agent.name, role_key: agent.role_key, system_prompt: agent.system_prompt });
  }

  function openAdd() {
    setAdding(true);
    setForm({ name: "", role_key: "", system_prompt: "" });
  }

  function handleSave() {
    if (editing) {
      updateAgent.mutate({
        agentId: editing.id,
        data: { name: form.name, system_prompt: form.system_prompt },
      }, { onSuccess: () => setEditing(null) });
    }
  }

  function handleCreate() {
    createAgent.mutate(form, { onSuccess: () => setAdding(false) });
  }

  const ROLE_COLORS: Record<string, string> = {
    architect: "bg-purple-500",
    developer: "bg-blue-500",
    reviewer: "bg-emerald-500",
    qa: "bg-orange-500",
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Agents</label>
        <Button type="button" variant="outline" size="sm" onClick={openAdd}>
          <Plus className="size-3.5 mr-1" />
          Add Agent
        </Button>
      </div>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading...</p>
      ) : agents && agents.length > 0 ? (
        <div className="space-y-1">
          {agents.map((a) => (
            <div key={a.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={`size-3 rounded-full shrink-0 ${ROLE_COLORS[a.role_key] || "bg-gray-500"}`}
                />
                <span className="font-medium">{a.name}</span>
                <span className="text-xs text-muted-foreground">{a.role_key}</span>
                {!a.enabled && (
                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded">Disabled</span>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => openEdit(a)}
                >
                  <Pencil className="size-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  disabled={deleteAgent.isPending}
                  onClick={() => deleteAgent.mutate(a.id)}
                >
                  <Trash2 className="size-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          No agents defined yet. Default agents are created automatically when needed.
        </p>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editing} onOpenChange={() => setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Agent</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="text-sm font-medium">System Prompt</label>
              <Textarea
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                rows={6}
                className="font-mono text-xs"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={handleSave} disabled={updateAgent.isPending}>
              {updateAgent.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Dialog */}
      <Dialog open={adding} onOpenChange={() => setAdding(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Agent</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Architect" />
            </div>
            <div>
              <label className="text-sm font-medium">Role Key</label>
              <Input value={form.role_key} onChange={(e) => setForm({ ...form, role_key: e.target.value })} placeholder="architect" />
            </div>
            <div>
              <label className="text-sm font-medium">System Prompt</label>
              <Textarea
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                rows={4}
                className="font-mono text-xs"
                placeholder="You are a..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAdding(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={createAgent.isPending}>
              {createAgent.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
