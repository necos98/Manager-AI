import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { MemoryTree } from "@/features/memories/components/memory-tree";
import { MemoryDetail } from "@/features/memories/components/memory-detail";
import { MemorySearch } from "@/features/memories/components/memory-search";

export const Route = createFileRoute("/projects/$projectId/memories")({
  component: MemoriesPage,
});

function MemoriesPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    document.title = project ? `Memories - ${project.name}` : "Memories";
  }, [project]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        {project && <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>}
        <h1 className="text-xl font-semibold">Memories</h1>
      </div>

      <div className="flex flex-1 min-h-0">
        <aside className="w-72 border-r flex flex-col min-h-0">
          <MemorySearch projectId={projectId} onSelect={setSelectedId} />
          <div className="flex-1 overflow-auto py-2">
            <MemoryTree projectId={projectId} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
        </aside>
        <main className="flex-1 min-w-0">
          <MemoryDetail memoryId={selectedId} onSelect={setSelectedId} />
        </main>
      </div>
    </div>
  );
}
