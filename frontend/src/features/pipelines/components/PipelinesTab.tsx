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
  ToggleLeft,
  ToggleRight,
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
  useUpdateEventRule,
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

const EVENT_TYPE_LABELS: Record<string, { label: string; verb: string }> = {
  step_completed: { label: "Step Completed", verb: "completes" },
  step_rejected: { label: "Step Rejected", verb: "is rejected" },
  step_failed: { label: "Step Failed", verb: "fails" },
  pipeline_completed: { label: "Pipeline Completed", verb: "pipeline completes" },
};

const ACTION_TYPE_LABELS: Record<string, string> = {
  redirect: "Redirect",
  set_issue_status: "Set Issue Status",
  emit_event: "Emit Custom Event",
};

function ruleDescription(rule: PipelineEventRule, steps: PipelineStep[], agents: Map<string, string>): string {
  const sourceName = ruleStepName(rule.source_step_id, steps, agents);
  const targetName = ruleStepName(rule.target_step_id, steps, agents);
  const evLabel = EVENT_TYPE_LABELS[rule.event_type]?.verb ?? rule.event_type;

  if (rule.action_type === "redirect") {
    return `When ${sourceName} ${evLabel} → go to ${targetName}`;
  }
  if (rule.action_type === "set_issue_status") {
    const status = (rule.action_params as Record<string, unknown> | null)?.status ?? "?";
    return `When ${sourceName} ${evLabel} → set issue status to ${status}`;
  }
  if (rule.action_type === "emit_event") {
    const eventName = (rule.action_params as Record<string, unknown> | null)?.event_type ?? "?";
    return `When ${sourceName} ${evLabel} → emit "${eventName}"`;
  }
  return `When ${sourceName} ${evLabel} → ${rule.action_type}`;
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
  const updateRule = useUpdateEventRule();

  // Form state
  const [eventType, setEventType] = useState("step_rejected");
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [actionType, setActionType] = useState("redirect");
  const [issueStatus, setIssueStatus] = useState("PLANNED");
  const [customEventType, setCustomEventType] = useState("");

  const resetForm = () => {
    setSourceId("");
    setTargetId("");
    setActionType("redirect");
    setIssueStatus("PLANNED");
    setCustomEventType("");
  };

  const handleAdd = () => {
    if (!sourceId) return;
    let actionParams: Record<string, unknown> | null = null;
    let effectiveTargetId = targetId;

    if (actionType === "set_issue_status") {
      actionParams = { status: issueStatus };
      effectiveTargetId = sourceId; // target_step is ignored for this action
    } else if (actionType === "emit_event") {
      if (!customEventType) return;
      actionParams = { event_type: customEventType };
      effectiveTargetId = sourceId; // target_step is ignored for this action
    } else {
      // redirect — target_step_id is the navigation target
      if (!targetId) return;
    }

    createRule.mutate(
      {
        pipelineId,
        data: {
          event_type: eventType,
          source_step_id: sourceId,
          target_step_id: effectiveTargetId,
          action_type: actionType,
          action_params: actionParams,
        },
      },
      { onSuccess: resetForm }
    );
  };

  const handleToggleEnabled = (rule: PipelineEventRule) => {
    updateRule.mutate({
      pipelineId,
      ruleId: rule.id,
      data: { enabled: !rule.enabled },
    });
  };

  const isValid =
    sourceId &&
    (actionType === "redirect" ? targetId : true) &&
    (actionType === "emit_event" ? customEventType : true);

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
              <Badge variant="outline" className="text-xs shrink-0">
                {rule.event_type}
              </Badge>
              <Badge
                variant="secondary"
                className={`text-xs shrink-0 ${
                  rule.action_type === "set_issue_status"
                    ? "bg-blue-500/10 text-blue-600"
                    : rule.action_type === "emit_event"
                      ? "bg-purple-500/10 text-purple-600"
                      : ""
                }`}
              >
                {ACTION_TYPE_LABELS[rule.action_type] ?? rule.action_type}
              </Badge>
              <span className="text-xs text-muted-foreground truncate flex-1">
                {ruleDescription(rule, steps, agents)}
              </span>
              <button
                type="button"
                className="size-6 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                disabled={updateRule.isPending}
                onClick={() => handleToggleEnabled(rule)}
                title={rule.enabled ? "Disable rule" : "Enable rule"}
              >
                {rule.enabled ? (
                  <ToggleRight className="size-4 text-green-600" />
                ) : (
                  <ToggleLeft className="size-4 text-muted-foreground" />
                )}
              </button>
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-destructive hover:text-destructive"
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
      <div className="flex flex-wrap items-center gap-2 pt-1">
        {/* Event type */}
        <Select value={eventType} onValueChange={setEventType}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Event type..." />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(EVENT_TYPE_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Action type */}
        <Select value={actionType} onValueChange={setActionType}>
          <SelectTrigger className="h-8 w-36 text-xs">
            <SelectValue placeholder="Action..." />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(ACTION_TYPE_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Source step */}
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

        {/* Conditional fields based on action_type */}
        {actionType === "redirect" && (
          <>
            <span className="text-xs text-muted-foreground">→ go to</span>
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
          </>
        )}

        {actionType === "set_issue_status" && (
          <>
            <span className="text-xs text-muted-foreground">→ set status</span>
            <Select value={issueStatus} onValueChange={setIssueStatus}>
              <SelectTrigger className="h-8 w-28 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PLANNED">PLANNED</SelectItem>
                <SelectItem value="ACCEPTED">ACCEPTED</SelectItem>
                <SelectItem value="FINISHED">FINISHED</SelectItem>
                <SelectItem value="CANCELED">CANCELED</SelectItem>
              </SelectContent>
            </Select>
          </>
        )}

        {actionType === "emit_event" && (
          <>
            <span className="text-xs text-muted-foreground">→ emit</span>
            <Input
              value={customEventType}
              onChange={(e) => setCustomEventType(e.target.value)}
              placeholder="event_type..."
              className="h-8 w-36 text-xs"
            />
          </>
        )}

        <Button
          size="sm"
          className="h-8 text-xs"
          disabled={!isValid || createRule.isPending}
          onClick={handleAdd}
        >
          {createRule.isPending ? (
            <Loader2 className="size-3 mr-1 animate-spin" />
          ) : (
            <Plus className="size-3 mr-1" />
          )}
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
