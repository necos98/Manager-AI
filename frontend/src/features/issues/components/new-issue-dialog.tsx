import { useCallback, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  ChevronsDown,
  ChevronsUp,
  Equal,
  FilePlus,
  Mic,
  Paperclip,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useCreateIssue, useProjectTags } from "@/features/issues/hooks";
import { TagInput } from "./tag-input";
import { FileGalleryModal } from "@/features/files/components/file-gallery-modal";
import { SpeechModal } from "@/shared/components/speech-modal";
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
import type { ProjectFile } from "@/shared/types";

type PriorityLevel = 1 | 2 | 3 | 4 | 5;

const PRIORITIES: { value: PriorityLevel; label: string; Icon: LucideIcon }[] = [
  { value: 1, label: "1 (Highest)", Icon: ChevronsUp },
  { value: 2, label: "2", Icon: ChevronUp },
  { value: 3, label: "3", Icon: Equal },
  { value: 4, label: "4", Icon: ChevronDown },
  { value: 5, label: "5 (Lowest)", Icon: ChevronsDown },
];

const DESCRIPTION_MAX = 50_000;

const CATEGORIES = [
  "Bug", "Feature", "Improvement", "Documentation",
  "Refactor", "Security", "Performance", "UI/UX",
];

type Props = {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function NewIssueDialog({ projectId, open, onOpenChange }: Props) {
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(3);
  const [tags, setTags] = useState<string[]>([]);
  const [category, setCategory] = useState<string | null>(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [speechOpen, setSpeechOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const createIssue = useCreateIssue(projectId);
  const { data: availableTags } = useProjectTags(projectId);

  const reset = () => {
    setDescription("");
    setPriority(3);
    setTags([]);
    setCategory(null);
  };

  const handleFileSelect = useCallback((file: ProjectFile) => {
    const tag = `@.manager_ai/resources/${file.stored_name} `;
    const textarea = textareaRef.current;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      setDescription((prev) => prev.slice(0, start) + tag + prev.slice(end));
      requestAnimationFrame(() => {
        const newPos = start + tag.length;
        textarea.selectionStart = newPos;
        textarea.selectionEnd = newPos;
        textarea.focus();
      });
    } else {
      setDescription((prev) => prev + tag);
    }
    setGalleryOpen(false);
  }, []);

  const handleSpeechSend = useCallback((text: string) => {
    setSpeechOpen(false);
    const textarea = textareaRef.current;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      setDescription((prev) => prev.slice(0, start) + text + prev.slice(end));
      requestAnimationFrame(() => {
        const newPos = start + text.length;
        textarea.selectionStart = newPos;
        textarea.selectionEnd = newPos;
        textarea.focus();
      });
    } else {
      setDescription((prev) => prev + text);
    }
  }, []);

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const tooLong = description.length > DESCRIPTION_MAX;
  const disabled = !description.trim() || tooLong || createIssue.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled) return;
    createIssue.mutate(
      { description, priority, category, tags },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
          toast.success("Issue created");
        },
      },
    );
  };

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
              ref={textareaRef}
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
            <div className="flex gap-2 mt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setGalleryOpen(true)}
              >
                <Paperclip className="size-4 mr-2" />
                Browse Files
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setSpeechOpen(true)}
                title="Voice input"
                aria-label="Voice input"
              >
                <Mic className="size-4 mr-2" />
                Voice
              </Button>
            </div>
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
                {PRIORITIES.map(({ value, label, Icon }) => (
                  <SelectItem key={value} value={String(value)}>
                    <span className="flex items-center gap-2">
                      <Icon className="size-4 text-muted-foreground" />
                      {label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Tags</label>
            <TagInput
              tags={tags}
              onChange={setTags}
              availableTags={availableTags ?? []}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Category</label>
            <Select
              value={category ?? "none"}
              onValueChange={(v) => setCategory(v === "none" ? null : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="No category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No category</SelectItem>
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
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
      <FileGalleryModal
        open={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        projectId={projectId}
        onSelect={handleFileSelect}
      />
      <SpeechModal
        open={speechOpen}
        onClose={() => setSpeechOpen(false)}
        onSend={handleSpeechSend}
      />
    </Dialog>
  );
}
