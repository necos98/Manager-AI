import { useState } from "react";
import { Plus, Pencil, Trash2, Bot, Loader2, Sprout, Play } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import { Badge } from "@/shared/components/ui/badge";
import { Skeleton } from "@/shared/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  useAgents,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useSeedAgents,
} from "@/features/agents/hooks";
import { useCreateManageAgentTerminal } from "@/features/terminals/hooks";
import type { Agent, AgentCreate, AgentUpdate } from "@/shared/types";

interface AgentsTabProps {
  projectId?: string;
}

interface AgentFormData {
  name: string;
  intent: string;
  model: string;
  allowed_tools: string;
}

const EMPTY_FORM: AgentFormData = {
  name: "",
  intent: "",
  model: "",
  allowed_tools: "",
};

function agentToForm(a: Agent): AgentFormData {
  return {
    name: a.name,
    intent: a.intent ?? "",
    model: a.model ?? "",
    allowed_tools: a.allowed_tools?.join(", ") ?? "",
  };
}

function formToCreate(data: AgentFormData): AgentCreate {
  return {
    name: data.name.trim(),
    intent: data.intent.trim() || undefined,
    model: data.model.trim() || null,
    allowed_tools: data.allowed_tools
      ? data.allowed_tools.split(",").map((t) => t.trim()).filter(Boolean)
      : null,
  };
}

function formToUpdate(data: AgentFormData): AgentUpdate {
  return {
    name: data.name.trim(),
    intent: data.intent.trim() || null,
    model: data.model.trim() || null,
    allowed_tools: data.allowed_tools
      ? data.allowed_tools.split(",").map((t) => t.trim()).filter(Boolean)
      : null,
  };
}

function validateForm(data: AgentFormData): string | null {
  if (!data.name.trim()) return "Name is required.";
  return null;
}

export function AgentsTab({ projectId: _projectId }: AgentsTabProps) {
  const { data: agents, isLoading, isError } = useAgents();
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent();
  const deleteAgent = useDeleteAgent();
  const seedAgents = useSeedAgents();
  const startAgentTerminal = useCreateManageAgentTerminal();
  const navigate = useNavigate();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form, setForm] = useState<AgentFormData>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null);
  const [startingAgentId, setStartingAgentId] = useState<string | null>(null);

  const openCreate = () => {
    setEditingAgent(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setDialogOpen(true);
  };

  const openEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setForm(agentToForm(agent));
    setFormError(null);
    setDialogOpen(true);
  };

  const handleSave = () => {
    const err = validateForm(form);
    if (err) {
      setFormError(err);
      return;
    }
    if (editingAgent) {
      updateAgent.mutate(
        { agentId: editingAgent.id, data: formToUpdate(form) },
        { onSuccess: () => setDialogOpen(false) }
      );
    } else {
      createAgent.mutate(formToCreate(form), {
        onSuccess: () => setDialogOpen(false),
      });
    }
  };

  const handleDelete = () => {
    if (!deleteTarget) return;
    deleteAgent.mutate(deleteTarget.id, {
      onSuccess: () => setDeleteTarget(null),
    });
  };

  const handleStartAgent = (agent: Agent) => {
    setStartingAgentId(agent.id);
    startAgentTerminal.mutate(
      { agent_id: agent.id },
      {
        onSuccess: () => {
          setStartingAgentId(null);
          navigate({ to: "/terminals" });
        },
        onError: () => {
          setStartingAgentId(null);
        },
      }
    );
  };

  const isMutating = createAgent.isPending || updateAgent.isPending;

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-9 w-28" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load agents.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Agents</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => seedAgents.mutate()}
            disabled={seedAgents.isPending}
          >
            <Sprout className="size-4 mr-1" />
            {seedAgents.isPending ? "Seeding..." : "Seed Defaults"}
          </Button>
          <Button size="sm" onClick={openCreate}>
            <Plus className="size-4 mr-1" />
            Create Agent
          </Button>
        </div>
      </div>

      {/* Empty state */}
      {(!agents || agents.length === 0) ? (
        <div className="text-center py-12 text-muted-foreground border rounded-lg">
          <Bot className="size-10 mx-auto mb-3 opacity-40" />
          <p>No agents configured.</p>
          <p className="text-sm">Seed defaults or create one to get started.</p>
        </div>
      ) : (
        /* Table */
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-muted/50 border-b">
                <th className="text-left px-4 py-3 text-sm font-medium">Name</th>
                <th className="text-left px-4 py-3 text-sm font-medium">Model</th>
                <th className="text-left px-4 py-3 text-sm font-medium">Tools</th>
                <th className="w-0 px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Bot className="size-4 text-muted-foreground" />
                      <span className="font-medium text-sm">{agent.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {agent.model ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    {agent.allowed_tools && agent.allowed_tools.length > 0 ? (
                      <Badge variant="secondary" className="text-xs">
                        {agent.allowed_tools.length}
                      </Badge>
                    ) : (
                      <span className="text-sm text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => handleStartAgent(agent)}
                        disabled={startingAgentId === agent.id}
                        aria-label={`Start ${agent.name}`}
                        title={`Start ${agent.name}`}
                      >
                        {startingAgentId === agent.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Play className="size-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => openEdit(agent)}
                        aria-label={`Edit ${agent.name}`}
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-destructive hover:text-destructive"
                        onClick={() => setDeleteTarget(agent)}
                        aria-label={`Delete ${agent.name}`}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingAgent ? "Edit Agent" : "Create Agent"}
            </DialogTitle>
            <DialogDescription>
              {editingAgent
                ? "Update the agent configuration."
                : "Add a new agent to the project."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-2">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="SpecWriter"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Intent</label>
              <Textarea
                value={form.intent}
                onChange={(e) => setForm({ ...form, intent: e.target.value })}
                placeholder="You are a specification writer..."
                rows={4}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Model (optional)</label>
              <Input
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                placeholder="claude-sonnet-4-6"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Allowed Tools (comma-separated, optional)</label>
              <Input
                value={form.allowed_tools}
                onChange={(e) => setForm({ ...form, allowed_tools: e.target.value })}
                placeholder="read, write, execute"
              />
            </div>
            {formError && (
              <p className="text-sm text-destructive">{formError}</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={isMutating}>
              {isMutating ? (
                <Loader2 className="size-4 mr-1 animate-spin" />
              ) : null}
              {isMutating ? "Saving..." : editingAgent ? "Save" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent?</DialogTitle>
            <DialogDescription>
              This will permanently delete{" "}
              <strong>{deleteTarget?.name}</strong>. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteAgent.isPending}
            >
              {deleteAgent.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
