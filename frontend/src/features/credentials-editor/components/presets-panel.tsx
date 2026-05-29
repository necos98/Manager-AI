import { useState } from "react";
import { Check, Pencil, Plus, Trash2 } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import type { PresetOut } from "../api";

interface Props {
  presets: PresetOut[];
  onCreate: (name: string) => void;
  onUpdate: (id: string, name: string) => void;
  onDelete: (id: string) => void;
  onApply: (id: string) => void;
  isCreating: boolean;
  isDeleting: boolean;
  isApplying: boolean;
}

export function PresetsPanel({ presets, onCreate, onUpdate, onDelete, onApply, isCreating, isDeleting, isApplying }: Props) {
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [presetName, setPresetName] = useState("");
  const [applyTarget, setApplyTarget] = useState<PresetOut | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<PresetOut | null>(null);
  const [editTarget, setEditTarget] = useState<PresetOut | null>(null);
  const [editName, setEditName] = useState("");

  const handleSave = () => {
    if (!presetName.trim()) return;
    onCreate(presetName.trim());
    setPresetName("");
    setSaveDialogOpen(false);
  };

  const handleEdit = () => {
    if (!editTarget || !editName.trim()) return;
    onUpdate(editTarget.id, editName.trim());
    setEditTarget(null);
    setEditName("");
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Presets</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {presets.length === 0 && (
            <p className="text-sm text-muted-foreground">No presets saved.</p>
          )}
          {presets.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span className="font-medium truncate mr-2">{p.name}</span>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => { setEditTarget(p); setEditName(p.name); }}
                >
                  <Pencil className="size-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => setDeleteTarget(p)}
                  disabled={isDeleting}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="size-3" />
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  onClick={() => setApplyTarget(p)}
                  disabled={isApplying}
                >
                  {isApplying ? "..." : <Check className="size-3 mr-1" />}
                  Apply
                </Button>
              </div>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" className="w-full mt-2" onClick={() => setSaveDialogOpen(true)}>
            <Plus className="size-3.5 mr-1" />
            Save Current as Preset
          </Button>
        </CardContent>
      </Card>

      {/* Save as Preset dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save as Preset</DialogTitle>
            <DialogDescription>Give this preset a name to reuse later.</DialogDescription>
          </DialogHeader>
          <Input
            placeholder="Preset name"
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSave(); }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={isCreating || !presetName.trim()}>
              {isCreating ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Apply confirmation dialog */}
      <Dialog open={!!applyTarget} onOpenChange={() => setApplyTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Apply Preset</DialogTitle>
            <DialogDescription>
              Replace current environment variables with <strong>{applyTarget?.name}</strong>? Current values will be overwritten.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApplyTarget(null)}>Cancel</Button>
            <Button
              onClick={() => {
                if (applyTarget) onApply(applyTarget.id);
                setApplyTarget(null);
              }}
              disabled={isApplying}
            >
              {isApplying ? "Applying..." : "Apply"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Preset</DialogTitle>
            <DialogDescription>
              Permanently delete <strong>{deleteTarget?.name}</strong>? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteTarget) onDelete(deleteTarget.id);
                setDeleteTarget(null);
              }}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit name dialog */}
      <Dialog open={!!editTarget} onOpenChange={() => setEditTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Preset</DialogTitle>
          </DialogHeader>
          <Input
            placeholder="Preset name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleEdit(); }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditTarget(null)}>Cancel</Button>
            <Button onClick={handleEdit} disabled={!editName.trim()}>
              Rename
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
