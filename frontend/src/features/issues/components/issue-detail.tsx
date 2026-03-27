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
import { TaskList } from "./task-list";
import { useDeleteIssue } from "@/features/issues/hooks";
import { useKillTerminal } from "@/features/terminals/hooks";
import type { Issue } from "@/shared/types";

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

  const tabs = useMemo<TabDef[]>(() => [
    { value: "description", label: "Description", available: true },
    { value: "specification", label: "Specification", available: !!issue.specification },
    { value: "plan", label: "Plan", available: !!issue.plan },
    { value: "tasks", label: "Tasks", available: !!(issue.tasks && issue.tasks.length > 0) },
    { value: "recap", label: "Recap", available: !!issue.recap },
  ], [issue.specification, issue.plan, issue.tasks, issue.recap]);

  const availableTabs = tabs.filter((t) => t.available);
  const defaultTab = availableTabs[0]?.value ?? "description";

  const handleDelete = async () => {
    if (terminalId) {
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch {
        // Terminal may already be dead
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-xl font-bold">{issue.name || "Untitled Issue"}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-muted-foreground">Priority: {issue.priority}</span>
            <StatusBadge status={issue.status} />
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          onClick={() => setShowDeleteConfirm(true)}
        >
          <Trash2 className="size-4 mr-1" />
          Delete
        </Button>
      </div>

      {/* Tabbed content */}
      <Tabs defaultValue={defaultTab} className="w-full">
        <TabsList>
          {availableTabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="description" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm">{issue.description}</p>
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
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {issue.tasks && issue.tasks.length > 0 && (
          <TabsContent value="tasks" className="mt-4">
            <Card>
              <CardContent className="pt-6">
                <TaskList tasks={issue.tasks} />
              </CardContent>
            </Card>
          </TabsContent>
        )}

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
