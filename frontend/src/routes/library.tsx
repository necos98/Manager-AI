import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useSkills, useAgents, useSkillDetail, useCreateSkill } from "@/features/library/hooks";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import { Skeleton } from "@/shared/components/ui/skeleton";
import type { SkillMeta, SkillCreate } from "@/shared/types";

export const Route = createFileRoute("/library")({
  component: LibraryPage,
});

// ── SkillCard ────────────────────────────────────────────────────────────────

interface SkillCardProps {
  skill: SkillMeta;
  selected: boolean;
  onClick: () => void;
}

function SkillCard({ skill, selected, onClick }: SkillCardProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-colors hover:bg-muted/50 ${
        selected ? "border-primary bg-muted/50" : "border-border"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="font-medium text-sm truncate">{skill.name}</span>
        <div className="flex gap-1 flex-shrink-0">
          <Badge variant="outline" className="text-xs">{skill.category}</Badge>
          {skill.built_in ? (
            <Badge variant="secondary" className="text-xs">Built-in</Badge>
          ) : (
            <Badge variant="secondary" className="text-xs">Custom</Badge>
          )}
        </div>
      </div>
      <p className="text-xs text-muted-foreground line-clamp-2">{skill.description}</p>
    </button>
  );
}

// ── CreateSkillDialog ────────────────────────────────────────────────────────

interface CreateSkillDialogProps {
  open: boolean;
  type: string;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: SkillCreate) => void;
  isPending: boolean;
}

function CreateSkillDialog({ open, type, onOpenChange, onCreate, isPending }: CreateSkillDialogProps) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onCreate({ name, category, description, content, type });
  }

  function handleOpenChange(value: boolean) {
    if (!value) {
      setName("");
      setCategory("");
      setDescription("");
      setContent("");
    }
    onOpenChange(value);
  }

  const label = type === "agent" ? "Agent" : "Skill";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New {label}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`my-${type}`}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Category</label>
            <Input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="tech"
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Description</label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short description"
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Content</label>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="# Content..."
              className="font-mono text-xs min-h-[160px]"
              required
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Creating..." : `Create ${label}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── LibraryPage ──────────────────────────────────────────────────────────────

function LibraryPage() {
  const { data: skills = [], isLoading: loadingSkills } = useSkills();
  const { data: agents = [], isLoading: loadingAgents } = useAgents();
  const createSkill = useCreateSkill();

  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selected, setSelected] = useState<SkillMeta | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [createType, setCreateType] = useState<string>("skill");

  const allItems: SkillMeta[] = [...skills, ...agents];
  const categories = ["all", ...Array.from(new Set(allItems.map((s) => s.category))).sort()];

  const { data: detail, isLoading: loadingDetail } = useSkillDetail(
    selected?.name ?? "",
    selected?.type ?? "skill",
  );

  const filtered =
    categoryFilter === "all"
      ? allItems
      : allItems.filter((s) => s.category === categoryFilter);

  function openCreate(type: string) {
    setCreateType(type);
    setDialogOpen(true);
  }

  function handleCreate(data: SkillCreate) {
    createSkill.mutate(
      { ...data, type: createType },
      {
        onSuccess: () => {
          setDialogOpen(false);
        },
      },
    );
  }

  const isLoading = loadingSkills || loadingAgents;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Library</h1>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => openCreate("skill")}>
            New Skill
          </Button>
          <Button size="sm" variant="outline" onClick={() => openCreate("agent")}>
            New Agent
          </Button>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex gap-1.5 mb-4">
        {categories.map((cat) => (
          <Button
            key={cat}
            size="sm"
            variant={categoryFilter === cat ? "default" : "outline"}
            className="text-xs capitalize"
            onClick={() => setCategoryFilter(cat)}
          >
            {cat}
          </Button>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-[300px_1fr] gap-6">
        {/* Left: skill list */}
        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-220px)]">
          {isLoading ? (
            [1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">No items found.</p>
          ) : (
            filtered.map((skill) => (
              <SkillCard
                key={`${skill.type}:${skill.name}`}
                skill={skill}
                selected={selected?.name === skill.name && selected?.type === skill.type}
                onClick={() => setSelected(skill)}
              />
            ))
          )}
        </div>

        {/* Right: detail preview */}
        <div className="border rounded-lg p-4 overflow-y-auto max-h-[calc(100vh-220px)]">
          {!selected ? (
            <p className="text-sm text-muted-foreground">Select an item to preview.</p>
          ) : loadingDetail ? (
            <div className="space-y-3">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          ) : detail ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-sm">{detail.name}</span>
                <Badge variant="outline" className="text-xs">{detail.category}</Badge>
                {detail.built_in ? (
                  <Badge variant="secondary" className="text-xs">Built-in</Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">Custom</Badge>
                )}
                <Badge variant="outline" className="text-xs capitalize">{detail.type}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">{detail.description}</p>
              <pre className="text-xs font-mono bg-muted rounded p-3 whitespace-pre-wrap overflow-x-auto">
                {detail.content}
              </pre>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Could not load detail.</p>
          )}
        </div>
      </div>

      <CreateSkillDialog
        key={`${createType}-${String(dialogOpen)}`}
        open={dialogOpen}
        type={createType}
        onOpenChange={setDialogOpen}
        onCreate={handleCreate}
        isPending={createSkill.isPending}
      />
    </div>
  );
}
