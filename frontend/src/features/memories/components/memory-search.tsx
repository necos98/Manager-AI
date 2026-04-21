import { useMemorySearch } from "@/features/memories/hooks";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";

interface SearchProps {
  projectId: string;
  onSelect: (memoryId: string) => void;
}

export function MemorySearch({ projectId, onSelect }: SearchProps) {
  const [input, setInput] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(input), 250);
    return () => clearTimeout(t);
  }, [input]);
  const { data } = useMemorySearch(projectId, debounced);

  return (
    <div className="relative">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Search className="size-4 text-muted-foreground" />
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search memories…"
          className="flex-1 bg-transparent text-sm outline-none"
        />
      </div>
      {debounced && data && data.length > 0 && (
        <ul className="absolute left-0 right-0 z-10 max-h-80 overflow-auto border-b bg-popover shadow">
          {data.map((hit) => (
            <li key={hit.memory.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(hit.memory.id);
                  setInput("");
                  setDebounced("");
                }}
                className="flex w-full flex-col px-3 py-2 text-left hover:bg-accent"
              >
                <span className="text-sm font-medium">{hit.memory.title}</span>
                <span className="text-xs text-muted-foreground" dangerouslySetInnerHTML={{ __html: hit.snippet }} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
