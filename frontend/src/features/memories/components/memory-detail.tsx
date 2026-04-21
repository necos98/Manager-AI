import { useMemory } from "@/features/memories/hooks";
import type { Memory, MemoryLink } from "@/shared/types";
import ReactMarkdown from "react-markdown";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface DetailProps {
  memoryId: string | null;
  onSelect: (memoryId: string) => void;
}

export function MemoryDetail({ memoryId, onSelect }: DetailProps) {
  const { data, isLoading } = useMemory(memoryId);
  if (!memoryId) return <div className="p-6 text-sm text-muted-foreground">Select a memory.</div>;
  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
      </div>
    );
  }
  return (
    <div className="p-6 space-y-5 overflow-auto">
      <header>
        <h2 className="text-lg font-semibold">{data.title}</h2>
        <p className="text-xs text-muted-foreground">
          Created {new Date(data.created_at).toLocaleString()} · Updated {new Date(data.updated_at).toLocaleString()}
        </p>
      </header>

      <section className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{data.description || "*(no description)*"}</ReactMarkdown>
      </section>

      {data.parent && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Parent</h3>
          <MemoryPill memory={data.parent} onSelect={onSelect} />
        </section>
      )}

      {data.children.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Children</h3>
          <ul className="space-y-1">
            {data.children.map((c) => (
              <li key={c.id}>
                <MemoryPill memory={c} onSelect={onSelect} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.links_out.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Links out</h3>
          <ul className="space-y-1">
            {data.links_out.map((l) => (
              <li key={`${l.from_id}-${l.to_id}-${l.relation}`}>
                <LinkRow link={l} otherId={l.to_id} onSelect={onSelect} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.links_in.length > 0 && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Links in</h3>
          <ul className="space-y-1">
            {data.links_in.map((l) => (
              <li key={`${l.from_id}-${l.to_id}-${l.relation}`}>
                <LinkRow link={l} otherId={l.from_id} onSelect={onSelect} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function MemoryPill({ memory, onSelect }: { memory: Memory; onSelect: (id: string) => void }) {
  return (
    <button type="button" onClick={() => onSelect(memory.id)} className="rounded border px-2 py-1 text-sm hover:bg-accent">
      {memory.title}
    </button>
  );
}

function LinkRow({ link, otherId, onSelect }: { link: MemoryLink; otherId: string; onSelect: (id: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(otherId)}
      className="flex items-center gap-2 rounded border px-2 py-1 text-sm hover:bg-accent"
    >
      <span className="font-mono text-xs text-muted-foreground">{link.relation || "—"}</span>
      <span className="font-mono text-xs">{otherId.slice(0, 8)}</span>
    </button>
  );
}
