import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/shared/components/ui/collapsible";
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

export function IssueDetail({ issue, projectId, terminalId }: IssueDetailProps) {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const deleteIssue = useDeleteIssue(projectId);
  const killTerminal = useKillTerminal();

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

      {/* Description */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold uppercase text-muted-foreground">
            Description
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">{issue.description}</p>
        </CardContent>
      </Card>

      {/* Specification */}
      {issue.specification && (
        <Collapsible defaultOpen>
          <Card>
            <CardHeader>
              <CollapsibleTrigger asChild>
                <CardTitle className="text-sm font-semibold uppercase text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  Specification
                </CardTitle>
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent>
                <MarkdownViewer content={issue.specification} />
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Plan */}
      {issue.plan && (
        <Collapsible defaultOpen>
          <Card>
            <CardHeader>
              <CollapsibleTrigger asChild>
                <CardTitle className="text-sm font-semibold uppercase text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  Plan
                </CardTitle>
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent>
                <MarkdownViewer content={issue.plan} />
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Tasks */}
      {issue.tasks && issue.tasks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold uppercase text-muted-foreground">
              Tasks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList tasks={issue.tasks} />
          </CardContent>
        </Card>
      )}

      {/* Recap */}
      {issue.recap && (
        <Collapsible defaultOpen>
          <Card>
            <CardHeader>
              <CollapsibleTrigger asChild>
                <CardTitle className="text-sm font-semibold uppercase text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  Recap
                </CardTitle>
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent>
                <MarkdownViewer content={issue.recap} />
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

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
