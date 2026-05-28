import { useState, useEffect } from "react";
import { Plus, Pencil, Trash2, Bot, Loader2, Sprout, Terminal } from "lucide-react";
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
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import {
  useAgents,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useSeedAgents,
} from "@/features/agents/hooks";
import {
  useCreateManageAgentTerminal,
  useManageAgentTerminals,
  useKillTerminal,
  terminalKeys,
} from "@/features/terminals/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { Agent, AgentCreate, AgentUpdate } from "@/shared/types";

interface AgentFormData {
  name: string;
  model: string;
  allowed_tools: string;
  intent: string;
}

const EMPTY_FORM: AgentFormData = {
  name: "",
  model: "",
  allowed_tools: "",
  intent: "",
};

function agentToForm(a: Agent): AgentFormData {
  return {
    name: a.name,
    model: a.model ?? "",
    allowed_tools: a.allowed_tools?.join(", ") ?? "",
    intent: a.intent ?? "",
  };
}

function formToCreate(data: AgentFormData): AgentCreate {
  return {
    name: data.name.trim(),
    model: data.model.trim() || null,
    allowed_tools: data.allowed_tools
      ? data.allowed_tools.split(",").map((t) => t.trim()).filter(Boolean)
      : null,
    intent: data.intent.trim(),
  };
}

function formToUpdate(data: AgentFormData): AgentUpdate {
  return {
    name: data.name.trim(),
    model: data.model.trim() || null,
    allowed_tools: data.allowed_tools
      ? data.allowed_tools.split(",").map((t) => t.trim()).filter(Boolean)
      : null,
    intent: data.intent.trim(),
  };
}

function validateForm(data: AgentFormData): string | null {
  if (!data.name.trim()) return "Name is required.";
  return null;
}

export function AgentsTab() {
  const { data: agents, isLoading, isError } = useAgents();
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent();
  const deleteAgent = useDeleteAgent();
  const seedAgents = useSeedAgents();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form, setForm] = useState<AgentFormData>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null);

  // ── Manage Agent terminal ──────────────────────────────────────────────

  const [terminalId, setTerminalId] = useState<string | null>(null);
  const createManageAgentTerminal = useCreateManageAgentTerminal();
  const killTerminal = useKillTerminal();
  const { data: manageTerminals, isLoading: manageTerminalsLoading } = useManageAgentTerminals();
  const queryClient = useQueryClient();

  // Reattach to existing manage-agent terminal on page mount
  useEffect(() => {
    if (terminalId) return;
    if (!manageTerminals || manageTerminals.length === 0) return;
    const latest = [...manageTerminals].sort((a, b) =>
      (b.created_at ?? "").localeCompare(a.created_at ?? ""),
    )[0];
    if (latest?.id) setTerminalId(latest.id);
  }, [manageTerminals, terminalId, setTerminalId]);

  const handleStartManageAgent = async () => {
    try {
      const terminal = await createManageAgentTerminal.mutateAsync({});
      setTerminalId(terminal.id);
      queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent });
    } catch (err) {
      toast.error("Failed to start session: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const handleEndSession = async () => {
    const current = terminalId;
    if (current) {
      try {
        await killTerminal.mutateAsync(current);
      } catch {
        // already gone
      }
    }
    setTerminalId(null);
    queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent });
  };

  // ── Agent CRUD ─────────────────────────────────────────────────────────

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

  const isMutating = createAgent.isPending || updateAgent.isPending;

  // ── Loading / Error states ────────────────────────────────────────────

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
    <div className="p-6 space-y-6">
      {/* ── Manage Agent Terminal Section ──────────────────────────────── */}
      {!terminalId ? (
        <div className="border rounded-lg p-6 flex flex-col items-center gap-3 bg-muted/30">
          <Terminal className="size-10 text-muted-foreground" />
          <div className="text-center">
            <h3 className="font-medium mb-1">Agent Manager</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Launch an interactive terminal session with Claude to create, edit, or delete agents using natural language.
            </p>
          </div>
          <Button
            onClick={handleStartManageAgent}
            disabled={createManageAgentTerminal.isPending || manageTerminalsLoading}
          >
            {createManageAgentTerminal.isPending ? "Starting..." : "Launch Agent Manager"}
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden" style={{ height: "400px" }}>
          <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
            <span className="text-sm font-medium">Agent Manager Session</span>
            <Button size="sm" variant="outline" onClick={handleEndSession}>
              End Session
            </Button>
          </div>
          <TerminalPanel
            terminalId={terminalId}
            projectId=""
            onSessionEnd={handleEndSession}
          />
        </div>
      )}

      {/* ── Agents Table ───────────────────────────────────────────────── */}
      <div className="space-y-4">
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
                  <th className="text-left px-4 py-3 text-sm font-medium">Intent</th>
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
                    <td className="px-4 py-3 text-sm text-muted-foreground max-w-80 truncate">
                      {agent.intent || "—"}
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
      </div>

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
            <div>
              <label className="text-sm font-medium">Intent</label>
              <Textarea
                value={form.intent}
                onChange={(e) => setForm({ ...form, intent: e.target.value })}
                placeholder="Describe what this agent does and its role in the pipeline..."
                rows={3}
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
