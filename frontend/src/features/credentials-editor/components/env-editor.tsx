import { useState } from "react";
import { Eye, EyeOff, Plus, Trash2 } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";

const SENSITIVE_PATTERNS = ["KEY", "SECRET", "TOKEN"];

function isSensitive(key: string): boolean {
  return SENSITIVE_PATTERNS.some((p) => key.toUpperCase().includes(p));
}

interface EnvRow {
  key: string;
  value: string;
}

interface Props {
  variables: Record<string, string>;
  onSave: (vars: Record<string, string>) => void;
  isSaving: boolean;
}

export function EnvEditor({ variables, onSave, isSaving }: Props) {
  const [rows, setRows] = useState<EnvRow[]>(() =>
    Object.entries(variables).map(([key, value]) => ({ key, value }))
  );
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const [removeTarget, setRemoveTarget] = useState<number | null>(null);

  const updateRow = (i: number, field: "key" | "value", val: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[i] = { ...next[i], [field]: val };
      return next;
    });
  };

  const addRow = () => {
    setRows((prev) => [...prev, { key: "", value: "" }]);
  };

  const handleSave = () => {
    const vars: Record<string, string> = {};
    for (const r of rows) {
      if (r.key.trim()) {
        vars[r.key.trim()] = r.value;
      }
    }
    onSave(vars);
  };

  const confirmRemove = () => {
    if (removeTarget === null) return;
    setRows((prev) => prev.filter((_, i) => i !== removeTarget));
    setRevealed((prev) => {
      const next = new Set(prev);
      next.delete(removeTarget);
      return next;
    });
    setRemoveTarget(null);
  };

  const toggleReveal = (i: number) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Environment Variables</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {rows.length === 0 && (
            <p className="text-sm text-muted-foreground">No variables. Add one below.</p>
          )}
          {rows.map((row, i) => {
            const sensitive = isSensitive(row.key);
            const showValue = !sensitive || revealed.has(i);
            return (
              <div key={i} className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <Input
                    placeholder="Key"
                    value={row.key}
                    onChange={(e) => updateRow(i, "key", e.target.value)}
                    className="font-mono text-xs"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="relative">
                    <Input
                      placeholder="Value"
                      type={showValue ? "text" : "password"}
                      value={row.value}
                      onChange={(e) => updateRow(i, "value", e.target.value)}
                      className="font-mono text-xs pr-8"
                    />
                    {sensitive && (
                      <button
                        type="button"
                        onClick={() => toggleReveal(i)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        tabIndex={-1}
                      >
                        {revealed.has(i) ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                      </button>
                    )}
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  className="mt-0.5 shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={() => {
                    if (row.value) {
                      setRemoveTarget(i);
                    } else {
                      setRows((prev) => prev.filter((_, j) => j !== i));
                    }
                  }}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            );
          })}
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={addRow}>
              <Plus className="size-3.5 mr-1" />
              Add Variable
            </Button>
            <Button type="button" size="sm" onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={removeTarget !== null} onOpenChange={() => setRemoveTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove variable?</DialogTitle>
            <DialogDescription>
              Remove <strong>{removeTarget !== null ? rows[removeTarget]?.key || "this variable" : ""}</strong> and its value. This will not be saved until you click Save.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmRemove}>
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
