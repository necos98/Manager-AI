import { useState, useRef, useEffect } from "react";
import {
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  ArrowUp,
  ArrowDown,
  X,
  Workflow,
  Loader2,
  Sprout,
  Check,
  Pencil,
  Download,
  Upload,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Badge } from "@/shared/components/ui/badge";
import { Skeleton } from "@/shared/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  usePipelines,
  useCreatePipeline,
  useUpdatePipeline,
  useDeletePipeline,
  useAddPipelineStep,
  useRemovePipelineStep,
  useReorderPipelineSteps,
  useSeedPipeline,
  useExportPipelines,
  useExportPipeline,
  useExportPipelinesBatch,
  useImportPipelinesPreview,
  useImportPipelinesConfirm,
  useEventRules,
  useCreateEventRule,
  useDeleteEventRule,
} from "@/features/pipelines/hooks";
import { useAgents } from "@/features/agents/hooks";
import { ImportPreviewModal } from "@/shared/components/ImportPreviewModal";
import type { Pipeline, PipelineEventRule, PipelineStep } from "@/shared/types";

interface PipelinesTabProps {
  projectId?: string;
}

function StepSummary({ steps, agents }: { steps: PipelineStep[]; agents: Map<string, string> }) {
  if (steps.length === 0) {
    return <span className="text-sm text-muted-foreground">No steps</span>;
  }
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {steps.map((step, i) => (
        <span key={step.id} className="flex items-center gap-1 text-sm">
          <Badge variant="secondary" className="text-xs font-normal">
            {agents.get(step.agent_id) ?? "Unknown"}
          </Badge>
          {i < steps.length - 1 && (
            <span className="text-muted-foreground text-xs">→</span>
          )}
        </span>
      ))}
    </div>
  );
}

function ruleStepName(
  stepId: string,
  steps: PipelineStep[],
  agents: Map<string, string>
): string {
  const step = steps.find((s) => s.id === stepId);
  if (!step) return "Unknown";
  return agents.get(step.agent_id) ?? "Unknown";
}

function EventRulesSection({
  pipelineId,
  steps,
  agents,
}: {
  pipelineId: string;
  steps: PipelineStep[];
  agents: Map<string, string>;
}) {
  const { data: rules = [] } = useEventRules(pipelineId);
  const createRule = useCreateEventRule();
  const deleteRule = useDeleteEventRule();
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");

  const handleAdd = () => {
    if (!sourceId || !targetId) return;
    createRule.mutate(
      {
        pipelineId,
        data: {
          event_type: "step_rejected",
          source_step_id: sourceId,
          target_step_id: targetId,
        },
      },
      {
        onSuccess: () => {
          setSourceId("");
          setTargetId("");
        },
      }
    );
  };

  return (
    <div className="space-y-2">
      {rules.length === 0 ? (
        <p className="text-sm text-muted-foreground py-1">
          No event rules configured.
        </p>
      ) : (
        <div className="space-y-1.5">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center gap-2 bg-muted/30 rounded px-3 py-2 text-sm"
            >
              <Badge variant="outline" className="text-xs">
                {rule.event_type}
              </Badge>
              <span className="text-muted-foreground">when</span>
              <span className="font-medium">
                {ruleStepName(rule.source_step_id, steps, agents)}
              </span>
              <span className="text-muted-foreground">rejects →</span>
              <span className="font-medium">
                {ruleStepName(rule.target_step_id, steps, agents)}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="size-6 ml-auto text-destructive hover:text-destructive"
                disabled={deleteRule.isPending}
                onClick={() =>
                  deleteRule.mutate({ pipelineId, ruleId: rule.id })
                }
              >
                <X className="size-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add rule form */}
      <div className="flex items-center gap-2 pt-1">
        <Select value={sourceId} onValueChange={setSourceId}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="When step..." />
          </SelectTrigger>
          <SelectContent>
            {steps.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {ruleStepName(s.id, steps, agents)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">rejects → go to</span>
        <Select value={targetId} onValueChange={setTargetId}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="Target step..." />
          </SelectTrigger>
          <SelectContent>
            {steps.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {ruleStepName(s.id, steps, agents)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          className="h-8 text-xs"
          disabled={!sourceId || !targetId || createRule.isPending}
          onClick={handleAdd}
        >
          <Plus className="size-3 mr-1" />
          Add Rule
        </Button>
      </div>
    </div>
  );
}

export function PipelinesTab({ projectId: _projectId }: PipelinesTabProps) {
  const { data: pipelines, isLoading, isError } = usePipelines();
  const { data: agentList } = useAgents();
  const createPipeline = useCreatePipeline();
  const updatePipeline = useUpdatePipeline();
  const deletePipeline = useDeletePipeline();
  const addStep = useAddPipelineStep();
  const removeStep = useRemovePipelineStep();
  const reorderSteps = useReorderPipelineSteps();
  const seedPipeline = useSeedPipeline();
  const exportPipelines = useExportPipelines();
  const exportPipeline = useExportPipeline();
  const importPreview = useImportPipelinesPreview();
  const importConfirm = useImportPipelinesConfirm();

  const agents = agentList ?? [];
  const agentMap = new Map(agents.map((a) => [a.id, a.name]));

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingNameId, setEditingNameId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [newPipelineName, setNewPipelineName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Pipeline | null>(null);

  // Step builder state
  const [newStepAgentId, setNewStepAgentId] = useState("");

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const startEditName = (pipeline: Pipeline) => {
    setEditingNameId(pipeline.id);
    setEditName(pipeline.name);
  };

  const saveEditName = (pipelineId: string) => {
    if (editName.trim()) {
      updatePipeline.mutate({ pipelineId, data: { name: editName.trim() } });
    }
    setEditingNameId(null);
  };

  const handleCreate = () => {
    if (!newPipelineName.trim()) return;
    createPipeline.mutate(
      { name: newPipelineName.trim() },
      { onSuccess: () => setNewPipelineName("") }
    );
  };

  const handleAddStep = (pipelineId: string) => {
    if (!newStepAgentId) return;
    addStep.mutate(
      {
        pipelineId,
        data: {
          agent_id: newStepAgentId,
        },
      },
      {
        onSuccess: () => {
          setNewStepAgentId("");
        },
      }
    );
  };

  const handleMoveStep = (pipelineId: string, stepIds: string[], from: number, dir: 1 | -1) => {
    const to = from + dir;
    if (to < 0 || to >= stepIds.length) return;
    const reordered = [...stepIds];
    [reordered[from], reordered[to]] = [reordered[to], reordered[from]];
    reorderSteps.mutate({ pipelineId, data: { step_ids: reordered } });
  };

  // Export/Import
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  const handleExportAll = () => {
    exportPipelines.mutate();
  };

  const handleExportPipeline = (pipelineId: string) => {
    exportPipeline.mutate(pipelineId);
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

  const isMutating =
    createPipeline.isPending ||
    updatePipeline.isPending ||
    addStep.isPending ||
    removeStep.isPending ||
    reorderSteps.isPending;

  // Batch selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const selectAllRef = useRef<HTMLInputElement>(null);
  const exportPipelinesBatch = useExportPipelinesBatch();

  const visibleIds = pipelines?.map((p) => p.id) ?? [];
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
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-36" />
          <Skeleton className="h-9 w-28" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load pipelines.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <input
            ref={selectAllRef}
            type="checkbox"
            checked={allSelected}
            onChange={toggleSelectAll}
            className="size-4"
          />
          <h2 className="text-lg font-semibold">Pipelines</h2>
        </div>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <span className="text-sm text-muted-foreground">
              {selectedIds.size} selected
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportPipelinesBatch.mutate([...selectedIds])}
            disabled={selectedIds.size === 0 || exportPipelinesBatch.isPending}
          >
            <Download className="size-4 mr-1" />
            {exportPipelinesBatch.isPending ? "Exporting..." : "Export Selected"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportAll}
            disabled={exportPipelines.isPending}
          >
            <Download className="size-4 mr-1" />
            {exportPipelines.isPending ? "Exporting..." : "Export All"}
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
          <Button
            variant="outline"
            size="sm"
            onClick={() => seedPipeline.mutate()}
            disabled={seedPipeline.isPending}
          >
            <Sprout className="size-4 mr-1" />
            {seedPipeline.isPending ? "Seeding..." : "Seed Default"}
          </Button>
        </div>
      </div>

      {/* Create pipeline */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="New pipeline name..."
          value={newPipelineName}
          onChange={(e) => setNewPipelineName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleCreate();
          }}
          className="max-w-xs"
        />
        <Button
          size="sm"
          onClick={handleCreate}
          disabled={!newPipelineName.trim() || createPipeline.isPending}
        >
          {createPipeline.isPending ? (
            <Loader2 className="size-4 mr-1 animate-spin" />
          ) : (
            <Plus className="size-4 mr-1" />
          )}
          Create
        </Button>
      </div>

      {/* Empty state */}
      {(!pipelines || pipelines.length === 0) ? (
        <div className="text-center py-12 text-muted-foreground border rounded-lg">
          <Workflow className="size-10 mx-auto mb-3 opacity-40" />
          <p>No pipelines configured.</p>
          <p className="text-sm">Create one or seed the default pipeline.</p>
        </div>
      ) : (
        /* Pipeline cards */
        <div className="space-y-3">
          {pipelines.map((pipeline) => {
            const isExpanded = expandedId === pipeline.id;
            const sortedSteps = [...pipeline.steps].sort(
              (a, b) => a.order_index - b.order_index
            );
            const stepIds = sortedSteps.map((s) => s.id);

            return (
              <div
                key={pipeline.id}
                className="border rounded-lg overflow-hidden"
              >
                {/* Card header */}
                <div className="flex items-center gap-2 px-4 py-3 bg-muted/20">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(pipeline.id)}
                    onChange={() => toggleSelect(pipeline.id)}
                    className="size-4"
                  />
                  <button
                    onClick={() => toggleExpand(pipeline.id)}
                    className="size-6 flex items-center justify-center"
                  >
                    {isExpanded ? (
                      <ChevronDown className="size-4" />
                    ) : (
                      <ChevronRight className="size-4" />
                    )}
                  </button>

                  <Workflow className="size-4 text-muted-foreground shrink-0" />

                  {editingNameId === pipeline.id ? (
                    <div className="flex items-center gap-1">
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-7 w-48 text-sm"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") saveEditName(pipeline.id);
                          if (e.key === "Escape") setEditingNameId(null);
                        }}
                        autoFocus
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6"
                        onClick={() => saveEditName(pipeline.id)}
                      >
                        <Check className="size-3" />
                      </Button>
                    </div>
                  ) : (
                    <span className="font-medium text-sm flex-1">
                      {pipeline.name}
                    </span>
                  )}

                  <StepSummary steps={sortedSteps} agents={agentMap} />

                  <div className="flex items-center gap-1 ml-auto">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => handleExportPipeline(pipeline.id)}
                      disabled={exportPipeline.isPending}
                      aria-label={`Export ${pipeline.name}`}
                    >
                      <Download className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => startEditName(pipeline)}
                      aria-label={`Rename ${pipeline.name}`}
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-destructive hover:text-destructive"
                      onClick={() => setDeleteTarget(pipeline)}
                      aria-label={`Delete ${pipeline.name}`}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>

                {/* Expanded step builder */}
                {isExpanded && (
                  <div className="px-4 py-3 border-t space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Steps
                    </p>

                    {sortedSteps.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-2">
                        No steps defined. Add a step below.
                      </p>
                    ) : (
                      <div className="space-y-1.5">
                        {sortedSteps.map((step, idx) => (
                          <div
                            key={step.id}
                            className="flex items-center gap-2 bg-muted/30 rounded px-3 py-2"
                          >
                            <span className="text-xs text-muted-foreground w-5">
                              {idx + 1}.
                            </span>
                            <span className="text-sm flex-1">
                              {agentMap.get(step.agent_id) ?? "Unknown"}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-6"
                              disabled={idx === 0 || reorderSteps.isPending}
                              onClick={() =>
                                handleMoveStep(pipeline.id, stepIds, idx, -1)
                              }
                            >
                              <ArrowUp className="size-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-6"
                              disabled={
                                idx === sortedSteps.length - 1 ||
                                reorderSteps.isPending
                              }
                              onClick={() =>
                                handleMoveStep(pipeline.id, stepIds, idx, 1)
                              }
                            >
                              <ArrowDown className="size-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-6 text-destructive hover:text-destructive"
                              disabled={removeStep.isPending}
                              onClick={() =>
                                removeStep.mutate({
                                  pipelineId: pipeline.id,
                                  stepId: step.id,
                                })
                              }
                            >
                              <X className="size-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add step form */}
                    <div className="flex items-center gap-2 pt-2 border-t">
                      <Select
                        value={newStepAgentId}
                        onValueChange={setNewStepAgentId}
                      >
                        <SelectTrigger className="h-8 w-48 text-xs">
                          <SelectValue placeholder="Select agent..." />
                        </SelectTrigger>
                        <SelectContent>
                          {agents.map((a) => (
                            <SelectItem key={a.id} value={a.id}>
                              {a.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        size="sm"
                        className="h-8 text-xs"
                        disabled={!newStepAgentId || addStep.isPending}
                        onClick={() => handleAddStep(pipeline.id)}
                      >
                        {addStep.isPending ? (
                          <Loader2 className="size-3 mr-1 animate-spin" />
                        ) : (
                          <Plus className="size-3 mr-1" />
                        )}
                        Add Step
                      </Button>
                    </div>

                    {/* Event Rules */}
                    <div className="pt-3 border-t mt-3">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                        Event Rules
                      </p>
                      <EventRulesSection
                        pipelineId={pipeline.id}
                        steps={sortedSteps}
                        agents={agentMap}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Import Preview Modal */}
      <ImportPreviewModal
        isOpen={importModalOpen}
        onClose={closeImportModal}
        title="Import Pipelines"
        previewData={importPreview.data as any ?? null}
        isLoading={importPreview.isPending}
        error={importPreview.error ? (importPreview.error instanceof Error ? importPreview.error.message : "Preview failed") : null}
        onConfirm={handleImportConfirm}
        isConfirming={importConfirm.isPending}
      />

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Pipeline?</DialogTitle>
            <DialogDescription>
              This will permanently delete{" "}
              <strong>{deleteTarget?.name}</strong> and all its steps. This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteTarget) {
                  deletePipeline.mutate(deleteTarget.id, {
                    onSuccess: () => setDeleteTarget(null),
                  });
                }
              }}
              disabled={deletePipeline.isPending}
            >
              {deletePipeline.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
