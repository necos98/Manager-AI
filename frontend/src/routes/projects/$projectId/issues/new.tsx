import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCreateIssue } from "@/features/issues/hooks";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";

export const Route = createFileRoute("/projects/$projectId/issues/new")({
  component: NewIssuePage,
});

function NewIssuePage() {
  const { projectId } = Route.useParams();
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(3);
  const createIssue = useCreateIssue(projectId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createIssue.mutate(
      { description, priority },
      {
        onSuccess: () => {
          navigate({
            to: "/projects/$projectId/issues",
            params: { projectId },
          });
        },
      },
    );
  };

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-xl font-bold mb-6">New Issue</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            placeholder="Describe what needs to be done..."
          />
        </div>

        <div>
          <label className="text-sm font-medium">Priority</label>
          <Select
            value={String(priority)}
            onValueChange={(v) => setPriority(Number(v))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1 (Highest)</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
              <SelectItem value="4">4</SelectItem>
              <SelectItem value="5">5 (Lowest)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {createIssue.error && (
          <p className="text-sm text-destructive">{createIssue.error.message}</p>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={createIssue.isPending}>
            {createIssue.isPending ? "Creating..." : "Create"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              navigate({ to: "/projects/$projectId/issues", params: { projectId } })
            }
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
