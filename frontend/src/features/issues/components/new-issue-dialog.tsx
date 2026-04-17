import { useState } from "react";
import { FilePlus } from "lucide-react";
import { toast } from "sonner";
import { useCreateIssue } from "@/features/issues/hooks";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";

const DESCRIPTION_MAX = 50_000;

type Props = {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function NewIssueDialog({ projectId, open, onOpenChange }: Props) {
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(3);
  const createIssue = useCreateIssue(projectId);

  const reset = () => {
    setDescription("");
    setPriority(3);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    createIssue.mutate(
      { description, priority },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
          toast.success("Issue created");
        },
      },
    );
  };

  const tooLong = description.length > DESCRIPTION_MAX;
  const disabled = !description.trim() || tooLong || createIssue.isPending;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FilePlus className="size-5 text-primary" />
            New Issue
          </DialogTitle>
          <DialogDescription>
            Describe what needs to be done. Claude will pick it up from here.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="new-issue-description" className="text-sm font-medium mb-1.5 block">
              Description <span className="text-destructive">*</span>
            </label>
            <Textarea
              id="new-issue-description"
              required
              autoFocus
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                  e.preventDefault();
                  handleSubmit(e as unknown as React.FormEvent);
                }
              }}
              rows={5}
              placeholder="Describe what needs to be done..."
            />
            <p
              className={`text-xs mt-1 text-right ${
                tooLong ? "text-destructive" : "text-muted-foreground"
              }`}
            >
              {description.length.toLocaleString()} / {DESCRIPTION_MAX.toLocaleString()}
            </p>
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Priority</label>
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

          <DialogFooter className="sm:justify-between sm:items-center">
            <span className="hidden sm:inline text-xs text-muted-foreground">
              <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono">⌘↵</kbd>{" "}
              to submit
            </span>
            <div className="flex gap-2 sm:justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={disabled}>
                {createIssue.isPending ? "Creating..." : "Create"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
