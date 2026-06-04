import { useState } from "react";
import { AlertTriangle, CheckSquare, Square } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import type { ImportConflict } from "@/shared/types";

interface ConflictModalProps {
  open: boolean;
  conflicts: ImportConflict[];
  onResolve: (overwriteIds: string[]) => void;
  onCancel: () => void;
  isResolving?: boolean;
}

export function ConflictModal({
  open,
  conflicts,
  onResolve,
  onCancel,
  isResolving,
}: ConflictModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set(conflicts.map((c) => c.existing_id)));

  const allSelected = selected.size === conflicts.length;

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(conflicts.map((c) => c.existing_id)));
  };

  return (
    <Dialog open={open} onOpenChange={() => onCancel()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-amber-500" />
            Import Conflicts Found
          </DialogTitle>
          <DialogDescription>
            {conflicts.length} entr{conflicts.length === 1 ? "y" : "ies"} with matching names already exist.
            Select which to overwrite.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1">
          <button
            onClick={toggleAll}
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground px-1 py-1.5 w-full text-left"
          >
            {allSelected ? <CheckSquare className="size-3.5" /> : <Square className="size-3.5" />}
            {allSelected ? "Deselect All" : "Select All"}
          </button>

          <ScrollArea className="max-h-64">
            <div className="space-y-1">
              {conflicts.map((c) => (
                <label
                  key={c.existing_id}
                  className="flex items-center gap-3 rounded px-3 py-2 hover:bg-muted cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(c.existing_id)}
                    onChange={() => toggle(c.existing_id)}
                    className="size-4"
                  />
                  <Badge
                    variant={c.type === "agent" ? "default" : "secondary"}
                    className="text-[10px] uppercase tracking-wider"
                  >
                    {c.type}
                  </Badge>
                  <span className="flex-1 font-medium">{c.name}</span>
                </label>
              ))}
            </div>
          </ScrollArea>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            onClick={() => onResolve(Array.from(selected))}
            disabled={selected.size === 0 || isResolving}
          >
            {isResolving
              ? "Importing..."
              : `Overwrite ${selected.size} / ${conflicts.length}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
