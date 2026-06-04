import { useState, useMemo } from "react";
import { Loader2, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Badge } from "@/shared/components/ui/badge";

interface ImportConflictItem {
  incoming: Record<string, unknown>;
  existing: Record<string, unknown>;
}

interface ImportPreviewData {
  conflicts: ImportConflictItem[];
  new: Record<string, unknown>[];
  total: number;
  missing_agents?: { agent_id: string; name: string }[];
}

interface ImportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  previewData: ImportPreviewData | null;
  isLoading: boolean;
  error: string | null;
  onConfirm: (conflicts: Record<string, string>) => void;
  isConfirming: boolean;
}

function getName(item: Record<string, unknown>): string {
  return (item.name as string) ?? (item.id as string) ?? "Unknown";
}

function ConflictSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: "skip" | "overwrite") => void;
}) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v as "skip" | "overwrite")}>
      <SelectTrigger className="h-8 w-28 text-xs">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="skip">Skip</SelectItem>
        <SelectItem value="overwrite">Overwrite</SelectItem>
      </SelectContent>
    </Select>
  );
}

export function ImportPreviewModal({
  isOpen,
  onClose,
  title,
  previewData,
  isLoading,
  error,
  onConfirm,
  isConfirming,
}: ImportPreviewModalProps) {
  const [conflictChoices, setConflictChoices] = useState<Record<string, string>>({});

  const totalImportable = useMemo(() => {
    if (!previewData) return 0;
    return previewData.new.length + previewData.conflicts.length;
  }, [previewData]);

  const handleConfirm = () => {
    onConfirm(conflictChoices);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open && !isConfirming) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {previewData && (
            <DialogDescription>
              {previewData.total} items found
              {previewData.conflicts.length > 0 && `, ${previewData.conflicts.length} conflicts`}
              {previewData.missing_agents && previewData.missing_agents.length > 0 &&
                `, ${previewData.missing_agents.length} missing dependencies`}
            </DialogDescription>
          )}
        </DialogHeader>

        <ScrollArea className="flex-1 -mx-6 px-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 p-3 rounded bg-destructive/10 text-destructive text-sm">
              <AlertTriangle className="size-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {previewData && (
            <div className="space-y-4 py-2">
              {/* New items */}
              {previewData.new.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-green-600 dark:text-green-400 mb-2">
                    <CheckCircle className="size-3.5 inline mr-1" />
                    New items ({previewData.new.length})
                  </h4>
                  <div className="space-y-1">
                    {previewData.new.map((item, i) => (
                      <div
                        key={i}
                        className="text-sm bg-green-50 dark:bg-green-950/30 rounded px-3 py-1.5"
                      >
                        {getName(item)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Conflicts */}
              {previewData.conflicts.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-amber-600 dark:text-amber-400 mb-2">
                    <AlertTriangle className="size-3.5 inline mr-1" />
                    Conflicts ({previewData.conflicts.length})
                  </h4>
                  <div className="space-y-2">
                    {previewData.conflicts.map((conflict, i) => {
                      const id = (conflict.incoming.id as string) ?? `conflict-${i}`;
                      const choice = conflictChoices[id] ?? "skip";
                      return (
                        <div
                          key={i}
                          className="border rounded p-3 text-sm space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{getName(conflict.incoming)}</span>
                            <ConflictSelect
                              value={choice}
                              onChange={(v) =>
                                setConflictChoices((prev) => ({ ...prev, [id]: v }))
                              }
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground border-t pt-1 mt-1">
                            <div>
                              <span className="font-medium">Existing:</span>{" "}
                              {getName(conflict.existing)}
                            </div>
                            <div>
                              <span className="font-medium">Incoming:</span>{" "}
                              {getName(conflict.incoming)}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Missing agents */}
              {previewData.missing_agents && previewData.missing_agents.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">
                    <XCircle className="size-3.5 inline mr-1" />
                    Missing agent dependencies ({previewData.missing_agents.length})
                  </h4>
                  <div className="space-y-1">
                    {previewData.missing_agents.map((ma, i) => (
                      <div
                        key={i}
                        className="text-sm bg-red-50 dark:bg-red-950/30 rounded px-3 py-1.5"
                      >
                        {ma.name} ({ma.agent_id.slice(0, 8)}...)
                      </div>
                    ))}
                    <p className="text-xs text-muted-foreground mt-1">
                      These agents must be imported first or already exist in the database.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isConfirming}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={
              !previewData || totalImportable === 0 || isConfirming || isLoading
            }
          >
            {isConfirming ? (
              <Loader2 className="size-4 mr-1 animate-spin" />
            ) : null}
            {isConfirming
              ? "Importing..."
              : `Confirm Import${totalImportable > 0 ? ` (${totalImportable})` : ""}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
