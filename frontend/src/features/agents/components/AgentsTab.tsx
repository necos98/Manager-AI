import { useState, useEffect, useRef } from "react";
import { Plus, Pencil, Trash2, Bot, Loader2, Sprout, MessageSquare, Download, Upload } from "lucide-react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  useAgents,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useSeedAgents,
  useExportAgents,
  useExportAgent,
  useExportAgentsBatch,
  useImportAgentsPreview,
  useImportAgentsConfirm,
} from "@/features/agents/hooks";
import {
  useCreateManageAgentTerminal,
  useManageAgentTerminals,
  useKillTerminal,
} from "@/features/terminals/hooks";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { ImportPreviewModal } from "@/shared/components/ImportPreviewModal";
import type { Agent, AgentCreate, AgentUpdate } from "@/shared/types";

interface AgentsTabProps {
  projectId?: string;
}

interface AgentFormData {
  name: string;
  provider: string;
  intent: string;
  model: string;
  allowed_tools: string;
}

const EMPTY_FORM: AgentFormData = {
  name: "",
  provider: "claude",
  intent: "",
  model: "",
  allowed_tools: "",
};

function agentToForm(a: Agent): AgentFormData {
  return {
    name: a.name,
    provider: a.provider ?? "claude",
    intent: a.intent ?? "",
    model: a.model ?? "",
    allowed_tools: a.allowed_tools?.join(", ") ?? "",
  };
}

function formToCreate(data: AgentFormData): AgentCreate {
  return {
    name: data.name.trim(),
    provider: data.provider,
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
    provider: data.provider,
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
  const exportAgents = useExportAgents();
  const exportAgent = useExportAgent();
  const importPreview = useImportAgentsPreview();
  const importConfirm = useImportAgentsConfirm();
  const createManageAgentTerminal = useCreateManageAgentTerminal();
  const { data: manageAgentTerminals, isPending: isManageTerminalsPending } = useManageAgentTerminals();
  const killTerminal = useKillTerminal();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form, setForm] = useState<AgentFormData>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null);
  const [chatTerminalId, setChatTerminalId] = useState<string | null>(null);
  const killedTerminalRef = useRef<string | null>(null);

  // Export/Import
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  const handleExportAll = () => {
    exportAgents.mutate();
  };

  const handleExportAgent = (agentId: string) => {
    exportAgent.mutate(agentId);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportFile(file);
    importPreview.mutate(file, {
      onSuccess: () => setImportModalOpen(true),
    });
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const handleImportConfirm = (conflicts: Record<string, string>) => {
    if (!importFile) return;
    importConfirm.mutate(
      { file: importFile, conflicts },
      {
        onSuccess: () => {
          setImportModalOpen(false);
          setImportFile(null);
        },
      },
    );
  };

  const closeImportModal = () => {
    if (importConfirm.isPending) return;
    setImportModalOpen(false);
    setImportFile(null);
    importPreview.reset();
  };

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

  const handleStartChat = async () => {
    try {
      const terminal = await createManageAgentTerminal.mutateAsync({});
      setChatTerminalId(terminal.id);
    } catch {
      // toast handled by hook
    }
  };

  const handleEndChat = async () => {
    if (chatTerminalId) {
      killedTerminalRef.current = chatTerminalId;
      try { await killTerminal.mutateAsync(chatTerminalId); } catch { /* already gone */ }
      setChatTerminalId(null);
    }
  };

  const isMutating = createAgent.isPending || updateAgent.isPending;

  // Batch selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const selectAllRef = useRef<HTMLInputElement>(null);
  const exportAgentsBatch = useExportAgentsBatch();

  const visibleIds = agents?.map((a) => a.id) ?? [];
  const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
  const someSelected = visibleIds.some((id) => selectedIds.has(id));

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected && !allSelected;
    }
  }, [someSelected, allSelected]);

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(visibleIds));
    }
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  // Reattach to existing manage-agent terminal on mount
  useEffect(() => {
    if (chatTerminalId) return;
    if (isManageTerminalsPending) return;
    if (!manageAgentTerminals || manageAgentTerminals.length === 0) return;
    const latest = [...manageAgentTerminals].sort((a, b) =>
      (b.created_at ?? "").localeCompare(a.created_at ?? ""),
    )[0];
    // Don't reattach if we just killed this terminal
    if (latest?.id && latest.id === killedTerminalRef.current) return;
    if (latest?.id) setChatTerminalId(latest.id);
  }, [manageAgentTerminals, chatTerminalId, isManageTerminalsPending]);

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
          {chatTerminalId ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleEndChat}
            >
              End Conversation
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartChat}
              disabled={createManageAgentTerminal.isPending}
            >
              <MessageSquare className="size-4 mr-1" />
              {createManageAgentTerminal.isPending ? "Starting..." : "Start Conversation"}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => seedAgents.mutate()}
            disabled={seedAgents.isPending}
          >
            <Sprout className="size-4 mr-1" />
            {seedAgents.isPending ? "Seeding..." : "Seed Defaults"}
          </Button>
          {selectedIds.size > 0 && (
            <span className="text-sm text-muted-foreground">
              {selectedIds.size} selected
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportAgentsBatch.mutate([...selectedIds])}
            disabled={selectedIds.size === 0 || exportAgentsBatch.isPending}
          >
            <Download className="size-4 mr-1" />
            {exportAgentsBatch.isPending ? "Exporting..." : "Export Selected"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportAll}
            disabled={exportAgents.isPending}
          >
            <Download className="size-4 mr-1" />
            {exportAgents.isPending ? "Exporting..." : "Export All"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleImportClick}
            disabled={importPreview.isPending}
          >
            <Upload className="size-4 mr-1" />
            {importPreview.isPending ? "Reading..." : "Import"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleFileSelected}
          />
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
                <th className="w-10 px-4 py-3">
                  <input
                    ref={selectAllRef}
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleSelectAll}
                    className="size-4"
                  />
                </th>
                <th className="text-left px-4 py-3 text-sm font-medium">Name</th>
                <th className="text-left px-4 py-3 text-sm font-medium">Provider</th>
                <th className="text-left px-4 py-3 text-sm font-medium">Model</th>
                <th className="text-left px-4 py-3 text-sm font-medium">Tools</th>
                <th className="w-0 px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(agent.id)}
                      onChange={() => toggleSelect(agent.id)}
                      className="size-4"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Bot className="size-4 text-muted-foreground" />
                      <span className="font-medium text-sm">{agent.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {agent.provider ? (
                      <Badge variant={agent.provider === "claude" ? "default" : "secondary"} className="text-xs font-mono">
                        {agent.provider}
                      </Badge>
                    ) : (
                      <span className="text-sm text-muted-foreground">—</span>
                    )}
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
                        onClick={() => handleExportAgent(agent.id)}
                        disabled={exportAgent.isPending}
                        aria-label={`Export ${agent.name}`}
                      >
                        <Download className="size-4" />
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

      {/* Manage Agent Terminal */}
      {chatTerminalId && (
        <div className="border rounded-lg overflow-hidden h-[400px] flex flex-col flex-shrink-0">
          <div className="flex-1 min-h-0">
            <TerminalPanel
              terminalId={chatTerminalId}
              projectId={_projectId}
              onSessionEnd={handleEndChat}
            />
          </div>
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
              <label className="text-sm font-medium">Provider</label>
              <Select
                value={form.provider}
                onValueChange={(v) => setForm({ ...form, provider: v })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="claude">Claude Code</SelectItem>
                  <SelectItem value="hermes">Hermes Agent</SelectItem>
                </SelectContent>
              </Select>
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

      {/* Import Preview Modal */}
      <ImportPreviewModal
        isOpen={importModalOpen}
        onClose={closeImportModal}
        title="Import Agents"
        previewData={importPreview.data as any ?? null}
        isLoading={importPreview.isPending}
        error={importPreview.error ? (importPreview.error instanceof Error ? importPreview.error.message : "Preview failed") : null}
        onConfirm={handleImportConfirm}
        isConfirming={importConfirm.isPending}
      />

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
