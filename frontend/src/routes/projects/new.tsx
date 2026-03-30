import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCreateProject } from "@/features/projects/hooks";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";

export const Route = createFileRoute("/projects/new")({
  component: NewProjectPage,
});

function NewProjectPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    path: "",
    description: "",
    tech_stack: "",
  });
  const createProject = useCreateProject();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createProject.mutate(form, {
      onSuccess: (project) => {
        navigate({
          to: "/projects/$projectId/issues",
          params: { projectId: project.id },
        });
      },
    });
  };

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-xl font-bold mb-6">New Project</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium">Name</label>
          <Input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </div>
        <div>
          <label className="text-sm font-medium">Path</label>
          <Input
            required
            value={form.path}
            onChange={(e) => setForm({ ...form, path: e.target.value })}
            className="font-mono"
            placeholder="/home/user/my-project"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={4}
            placeholder="Describe the project context..."
          />
        </div>
        <div>
          <label className="text-sm font-medium">Tech Stack</label>
          <Textarea
            value={form.tech_stack}
            onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
            rows={3}
            placeholder="Languages, frameworks, databases..."
          />
        </div>

        {createProject.error && (
          <p className="text-sm text-destructive">{createProject.error.message}</p>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={createProject.isPending}>
            {createProject.isPending ? "Creating..." : "Create"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate({ to: "/" })}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
