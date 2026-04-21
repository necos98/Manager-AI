import { useMemories } from "@/features/memories/hooks";
import type { Memory } from "@/shared/types";
import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";
import { cn } from "@/shared/lib/utils";

interface TreeProps {
  projectId: string;
  selectedId: string | null;
  onSelect: (memoryId: string) => void;
}

export function MemoryTree({ projectId, selectedId, onSelect }: TreeProps) {
  const roots = useMemories(projectId, null);
  if (roots.isLoading) return <div className="p-3 text-xs text-muted-foreground">Loading…</div>;
  if (!roots.data || roots.data.length === 0) {
    return <div className="p-3 text-xs text-muted-foreground">No memories yet.</div>;
  }
  return (
    <ul className="text-sm">
      {roots.data.map((m) => (
        <MemoryNode key={m.id} memory={m} projectId={projectId} depth={0} selectedId={selectedId} onSelect={onSelect} />
      ))}
    </ul>
  );
}

function MemoryNode({
  memory,
  projectId,
  depth,
  selectedId,
  onSelect,
}: {
  memory: Memory;
  projectId: string;
  depth: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const hasChildren = memory.children_count > 0;
  const children = useMemories(projectId, open ? memory.id : undefined);
  const isSelected = selectedId === memory.id;
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(memory.id)}
        className={cn(
          "flex w-full items-center gap-1 rounded px-2 py-1 text-left hover:bg-accent",
          isSelected && "bg-accent",
        )}
        style={{ paddingLeft: 8 + depth * 12 }}
      >
        <span
          role="button"
          tabIndex={0}
          onClick={(e) => {
            e.stopPropagation();
            if (hasChildren) setOpen((v) => !v);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && hasChildren) {
              e.stopPropagation();
              setOpen((v) => !v);
            }
          }}
          className="flex size-4 items-center justify-center"
          aria-label={hasChildren ? (open ? "Collapse" : "Expand") : undefined}
        >
          {hasChildren ? (
            open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />
          ) : (
            <Brain className="size-3 text-muted-foreground" />
          )}
        </span>
        <span className="truncate">{memory.title}</span>
      </button>
      {open && children.data && (
        <ul>
          {children.data.map((c) => (
            <MemoryNode key={c.id} memory={c} projectId={projectId} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </li>
  );
}
