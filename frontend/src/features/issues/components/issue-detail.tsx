import { useState, useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
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
import { useDeleteIssue, useUpdateIssue } from "@/features/issues/hooks";
import { useKillTerminal } from "@/features/terminals/hooks";
import type { Issue } from "@/shared/types";
import { IssueRelationsTab } from "./issue-relations-tab";

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

  const tabs = useMemo<TabDef[]>(() => [
    { value: "description", label: "Description", available: true },
    { value: "specification", label: "Specification", available: !!issue.specification },
    { value: "plan", label: "Plan", available: !!issue.plan },
    { value: "tasks", label: "Tasks", available: true },
    { value: "relations", label: "Relations", available: true },
    { value: "recap", label: "Recap", available: !!issue.recap },
  ], [issue.specification, issue.plan, issue.recap]);

  const availableTabs = tabs.filter((t) => t.available);
  const defaultTab = availableTabs[0]?.value ?? "description";

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
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive shrink-0"
          onClick={() => setShowDeleteConfirm(true)}
        >
          <Trash2 className="size-4 mr-1" />
          Delete
        </Button>
      </div>

      {/* Action buttons */}
      <IssueActions issue={issue} projectId={projectId} />

      {/* Tabbed content */}
      <Tabs defaultValue={defaultTab} className="w-full">
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
                renderView={(v) => <p className="text-sm whitespace-pre-wrap">{v}</p>}
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
