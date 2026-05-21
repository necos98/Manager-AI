import { useState, useMemo, useEffect } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Plus, Trash2, X } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { StatusBadge } from "./status-badge";
import { IssueActions } from "./issue-actions";
import { PlanFeedback } from "./plan-feedback";
import { EditableTaskList } from "./editable-task-list";
import { InlineEditField } from "./inline-edit-field";
import { TagInput } from "./tag-input";
import { useDeleteIssue, useUpdateIssue, useProjectTags } from "@/features/issues/hooks";
import { useKillTerminal } from "@/features/terminals/hooks";
import type { Issue } from "@/shared/types";
import { IssueRelationsTab } from "./issue-relations-tab";
import { AgentChat } from "@/features/agents/components/agent-chat";
import { PipelineProgress } from "@/features/agents/components/pipeline-progress";
import { usePipelineRunsForIssue, usePipelineRun } from "@/features/agents/hooks";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";

interface IssueDetailProps {
  issue: Issue;
  projectId: string;
  terminalId: string | null;
}

interface TabDef {
  value: string;
  label: string;
  available: boolean;
}

export function IssueDetail({ issue, projectId, terminalId }: IssueDetailProps) {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const deleteIssue = useDeleteIssue(projectId);
  const killTerminal = useKillTerminal();
  const updateIssue = useUpdateIssue(projectId, issue.id);
  const { data: availableTags } = useProjectTags(projectId);
  const [showTagInput, setShowTagInput] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("");

  const { data: pipelineRunsData } = usePipelineRunsForIssue(projectId, issue.id);
  const latestRun = pipelineRunsData?.runs?.[0];
  const { data: runDetail } = usePipelineRun(latestRun?.id ?? null);
  const steps = runDetail?.steps ?? [];
  const runningStep = steps.find((s) => s.status === "running");
  const pipelineLabel = latestRun
    ? latestRun.status === "running" && runningStep
      ? `Pipeline: Running (Step ${runningStep.step_order + 1}/${steps.length} — ${runningStep.agent_name})`
      : `Pipeline: ${latestRun.status.charAt(0).toUpperCase() + latestRun.status.slice(1)}`
    : null;

  const tabs = useMemo<TabDef[]>(() => [
    { value: "description", label: "Description", available: true },
    { value: "specification", label: "Specification", available: !!issue.specification },
    { value: "plan", label: "Plan", available: !!issue.plan },
    { value: "tasks", label: "Tasks", available: true },
    { value: "relations", label: "Relations", available: true },
    { value: "chat", label: "Agent Chat", available: true },
    { value: "pipeline", label: "Pipeline", available: true },
    { value: "recap", label: "Recap", available: !!issue.recap },
  ], [issue.specification, issue.plan, issue.recap]);

  const availableTabs = tabs.filter((t) => t.available);
  const defaultTab = availableTabs[0]?.value ?? "description";
  const currentTab = activeTab || defaultTab;

  const handleDelete = async () => {
    if (terminalId) {
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch (e) {
        // Terminal may already be dead — intentionally swallowed
        console.warn("killTerminal during delete:", e);
      }
    }
    deleteIssue.mutate(issue.id, {
      onSuccess: () => {
        navigate({
          to: "/projects/$projectId/issues",
          params: { projectId },
        });
      },
    });
  };

  const isTerminalState = issue.status === "Finished" || issue.status === "Canceled";

  const completedTaskCount = issue.tasks.filter((t) => t.status === "Completed").length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <InlineEditField
            value={issue.name || "Untitled Issue"}
            onSave={(name) => updateIssue.mutate({ name })}
            disabled={isTerminalState}
            validate={(v) => v.length > 500 ? "Max 500 characters" : null}
            renderView={(v) => <h1 className="text-xl font-bold">{v}</h1>}
          />
          <div className="flex items-center gap-3 mt-1">
            <InlineEditField
              value={String(issue.priority)}
              onSave={(v) => {
                const n = parseInt(v, 10);
                if (n >= 1 && n <= 5) updateIssue.mutate({ priority: n });
              }}
              disabled={isTerminalState}
              validate={(v) => {
                const n = parseInt(v, 10);
                return isNaN(n) || n < 1 || n > 5 ? "Priority must be 1-5" : null;
              }}
              renderView={(v) => (
                <span className="text-sm text-muted-foreground">Priority: {v}</span>
              )}
            />
            <StatusBadge status={issue.status} />
            <Select
              value={issue.category ?? "none"}
              onValueChange={(v) => updateIssue.mutate({ category: v === "none" ? null : v })}
              disabled={isTerminalState}
            >
              <SelectTrigger className="h-6 w-fit gap-1 border-0 px-2 text-xs font-medium">
                <SelectValue placeholder="No category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No category</SelectItem>
                {["Bug","Feature","Improvement","Documentation","Refactor","Security","Performance","UI/UX"].map((cat) => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {issue.tags && issue.tags.length > 0 && (
              <div className="flex flex-wrap items-center gap-1">
                {issue.tags.map(tag => (
                  <Link
                    key={tag}
                    to="/projects/$projectId/issues"
                    params={{ projectId }}
                    search={{ tag }}
                  >
                    <Badge variant="secondary" className="cursor-pointer hover:bg-secondary/80 gap-1 pr-1">
                      {tag}
                      {!isTerminalState && (
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            const newTags = (issue.tags || []).filter(t => t !== tag);
                            updateIssue.mutate({ tags: newTags });
                          }}
                          className="hover:text-destructive"
                        >
                          <X className="size-3" />
                        </button>
                      )}
                    </Badge>
                  </Link>
                ))}
              </div>
            )}
            {!isTerminalState && (
              <button
                onClick={() => setShowTagInput(!showTagInput)}
                className="text-muted-foreground hover:text-foreground"
              >
                <Plus className="size-4" />
              </button>
            )}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive shrink-0"
          onClick={() => setShowDeleteConfirm(true)}
          aria-label="Delete issue"
        >
          <Trash2 className="size-4 mr-1" />
          Delete
        </Button>
      </div>

      {showTagInput && (
        <div className="mt-2 max-w-sm">
          <TagInput
            tags={issue.tags || []}
            onChange={(newTags) => {
              updateIssue.mutate({ tags: newTags });
              if (newTags.length <= (issue.tags || []).length) {
                setShowTagInput(false);
              }
            }}
            availableTags={availableTags ?? []}
            placeholder="Add or remove tags..."
          />
        </div>
      )}

      {/* Action buttons */}
      <IssueActions issue={issue} projectId={projectId} />

      {/* Pipeline status badge */}
      {pipelineLabel && (
        <button
          className="w-full text-left px-3 py-1.5 rounded-md bg-muted/50 border text-xs font-medium hover:bg-muted transition-colors"
          onClick={() => setActiveTab("pipeline")}
        >
          {pipelineLabel}
        </button>
      )}

      {/* Tabbed content */}
      <Tabs value={currentTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          {availableTabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
              {tab.value === "tasks" && issue.tasks.length > 0 && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({completedTaskCount}/{issue.tasks.length})
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="description" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <InlineEditField
                value={issue.description}
                onSave={(description) => updateIssue.mutate({ description })}
                disabled={isTerminalState}
                multiline
                validate={(v) => v.length > 50_000 ? "Max 50,000 characters" : null}
                renderView={(v) => <MarkdownViewer content={v} />}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {issue.specification && (
          <TabsContent value="specification" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <MarkdownViewer content={issue.specification} />
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {issue.plan && (
          <TabsContent value="plan" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <MarkdownViewer content={issue.plan} />
                {issue.status === "Planned" && (
                  <PlanFeedback projectId={projectId} issueId={issue.id} />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        <TabsContent value="tasks" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <EditableTaskList
                tasks={issue.tasks}
                projectId={projectId}
                issueId={issue.id}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="relations">
          <IssueRelationsTab issue={issue} projectId={projectId} />
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          <AgentChat issueId={issue.id} />
        </TabsContent>

        <TabsContent value="pipeline" className="mt-4">
          <PipelineProgress projectId={projectId} issueId={issue.id} />
        </TabsContent>

        {issue.recap && (
          <TabsContent value="recap" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <MarkdownViewer content={issue.recap} />
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* Delete confirmation */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Issue?</DialogTitle>
            <DialogDescription>
              This will permanently delete this issue and all its tasks. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteIssue.isPending}
            >
              {deleteIssue.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
