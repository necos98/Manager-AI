import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { IssueRelationsGraph } from "./issue-relations-graph";
import { useRelations, useAddRelation, useDeleteRelation } from "@/features/issues/hooks-relations";
import { useIssues } from "@/features/issues/hooks";
import { Button } from "@/shared/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import type { Issue, RelationType } from "@/shared/types";

interface Props {
  issue: Issue;
  projectId: string;
}

export function IssueRelationsTab({ issue, projectId }: Props) {
  const navigate = useNavigate();
  const { data: relations = [] } = useRelations(issue.id);
  const { data: allIssues = [] } = useIssues(projectId);
  const addRelation = useAddRelation(issue.id);
  const deleteRelation = useDeleteRelation(issue.id);

  const [selectedIssueId, setSelectedIssueId] = useState("");
  const [relationType, setRelationType] = useState<RelationType>("blocks");

  const alreadyLinked = new Set([issue.id, ...relations.map((r) => r.source_id), ...relations.map((r) => r.target_id)]);
  const availableIssues = allIssues.filter((i) => !alreadyLinked.has(i.id));

  async function handleAdd() {
    if (!selectedIssueId) return;
    await addRelation.mutateAsync({ target_id: selectedIssueId, relation_type: relationType });
    setSelectedIssueId("");
  }

  return (
    <div className="space-y-4">
      <IssueRelationsGraph
        currentIssue={issue}
        relations={relations}
        allIssues={allIssues}
        onNavigate={(id) => navigate({ to: "/projects/$projectId/issues/$issueId", params: { projectId, issueId: id } })}
      />

      {/* Add relation form */}
      <div className="flex gap-2 flex-wrap">
        <Select value={selectedIssueId} onValueChange={setSelectedIssueId}>
          <SelectTrigger className="flex-1 min-w-[200px] h-8 text-sm">
            <SelectValue placeholder="Seleziona issue..." />
          </SelectTrigger>
          <SelectContent>
            {availableIssues.map((i) => (
              <SelectItem key={i.id} value={i.id}>
                {i.name || i.description.slice(0, 50)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={relationType} onValueChange={(v) => setRelationType(v as RelationType)}>
          <SelectTrigger className="w-[130px] h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="blocks">blocca</SelectItem>
            <SelectItem value="related">correlata</SelectItem>
          </SelectContent>
        </Select>
        <Button size="sm" onClick={handleAdd} disabled={!selectedIssueId || addRelation.isPending}>
          Aggiungi
        </Button>
      </div>

      {/* Relation list */}
      {relations.length > 0 && (
        <ul className="space-y-1">
          {relations.map((r) => {
            const other = allIssues.find((i) => i.id === (r.source_id === issue.id ? r.target_id : r.source_id));
            const direction = r.source_id === issue.id ? "→" : "←";
            const label = r.relation_type === "blocks" ? `${direction} blocca` : "↔ correlata";
            return (
              <li key={r.id} className="flex items-center justify-between text-sm p-2 rounded border">
                <span>
                  <span className="text-muted-foreground">{label}</span>{" "}
                  <span className="font-medium">{other?.name || other?.description?.slice(0, 40) || r.target_id}</span>
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-6 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteRelation.mutate(r.id)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
