// frontend/src/features/projects/components/library-tab.tsx
import { useState } from "react";
import { useSkills, useAgents } from "@/features/library/hooks";
import { useProjectSkills, useAssignSkill, useUnassignSkill } from "@/features/projects/hooks-skills";
import { useProjectTemplates, useSaveTemplate, useDeleteTemplate } from "@/features/projects/hooks-templates";
import type { SkillMeta, TemplateInfo } from "@/shared/types";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";

// ── Skills Section ────────────────────────────────────────────────────────────

function SkillsSection({ projectId }: { projectId: string }) {
  const { data: allSkills = [] } = useSkills();
  const { data: allAgents = [] } = useAgents();
  const { data: assigned = [] } = useProjectSkills(projectId);
  const assign = useAssignSkill(projectId);
  const unassign = useUnassignSkill(projectId);

  const assignedNames = new Set(assigned.map(s => `${s.type}:${s.name}`));

  const available = [
    ...allSkills.map(s => ({ ...s, type: "skill" as const })),
    ...allAgents.map(a => ({ ...a, type: "agent" as const })),
  ];

  const assignedItems = assigned.map(a => {
    const meta = available.find(s => s.name === a.name && s.type === a.type);
    return { ...a, description: meta?.description ?? "", category: meta?.category ?? "" };
  });

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Skills &amp; Agents</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-muted-foreground mb-2">Available in library</p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {available.map(skill => {
              const key = `${skill.type}:${skill.name}`;
              const isAssigned = assignedNames.has(key);
              return (
                <div key={key} className="flex items-start justify-between border rounded p-2 gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1">
                      <span className="text-xs font-medium truncate">{skill.name}</span>
                      <Badge variant="outline" className="text-xs shrink-0">{skill.category}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{skill.description}</p>
                  </div>
                  <Button
                    size="sm"
                    variant={isAssigned ? "secondary" : "outline"}
                    className="text-xs shrink-0"
                    disabled={isAssigned || assign.isPending}
                    onClick={() => assign.mutate({ name: skill.name, type: skill.type })}
                  >
                    {isAssigned ? "Active" : "Add"}
                  </Button>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <p className="text-xs text-muted-foreground mb-2">Active in this project</p>
          {assignedItems.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">No skills assigned yet.</p>
          ) : (
            <div className="space-y-2">
              {assignedItems.map(skill => (
                <div key={`${skill.type}:${skill.name}`} className="flex items-start justify-between border rounded p-2 border-primary/30 bg-primary/5 gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1">
                      <span className="text-xs font-medium truncate">{skill.name}</span>
                      <Badge variant="outline" className="text-xs shrink-0">{skill.category}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{skill.description}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs text-destructive shrink-0"
                    disabled={unassign.isPending}
                    onClick={() => unassign.mutate({ type: skill.type, name: skill.name })}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Templates Section ─────────────────────────────────────────────────────────

const TEMPLATE_LABELS: Record<string, string> = {
  workflow: "Workflow (spec + plan + tasks)",
  implementation: "Implementation",
  recap: "Recap (auto-completion)",
  spec: "Specification",
  plan: "Plan",
  enrich: "Context Enrichment",
};

const TEMPLATE_VARS = "{{issue_description}} {{issue_spec}} {{issue_plan}} {{project_name}} {{project_description}} {{tech_stack}} {{skills_context}}";

function TemplateRow({ tpl, projectId }: { tpl: TemplateInfo; projectId: string }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(tpl.content);
  const save = useSaveTemplate(projectId);
  const del = useDeleteTemplate(projectId);

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{TEMPLATE_LABELS[tpl.type] ?? tpl.type}</span>
          <Badge variant={tpl.is_overridden ? "default" : "secondary"} className="text-xs">
            {tpl.is_overridden ? "Custom" : "Default"}
          </Badge>
        </div>
        <div className="flex gap-1">
          {!editing && (
            <Button size="sm" variant="outline" className="text-xs" onClick={() => { setDraft(tpl.content); setEditing(true); }}>
              Edit
            </Button>
          )}
          {tpl.is_overridden && !editing && (
            <Button size="sm" variant="ghost" className="text-xs text-destructive" onClick={() => del.mutate(tpl.type)}>
              Reset
            </Button>
          )}
        </div>
      </div>

      {editing ? (
        <div className="space-y-2">
          <Textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={8}
            className="font-mono text-xs"
          />
          <p className="text-xs text-muted-foreground">Variables: {TEMPLATE_VARS}</p>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => { save.mutate({ type: tpl.type, content: draft }); setEditing(false); }}>
              Save
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </div>
      ) : (
        <pre className="text-xs bg-muted rounded p-2 max-h-24 overflow-hidden whitespace-pre-wrap text-muted-foreground">
          {tpl.content.slice(0, 200)}{tpl.content.length > 200 ? "…" : ""}
        </pre>
      )}
    </div>
  );
}

function TemplatesSection({ projectId }: { projectId: string }) {
  const { data: templates = [] } = useProjectTemplates(projectId);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold">Prompt Templates</h3>
      {templates.map(tpl => (
        <TemplateRow key={tpl.type} tpl={tpl} projectId={projectId} />
      ))}
    </div>
  );
}

// ── Main Export ───────────────────────────────────────────────────────────────

export function LibraryTab({ projectId }: { projectId: string }) {
  const [section, setSection] = useState<"skills" | "templates">("skills");

  return (
    <div className="space-y-6">
      <div className="flex gap-2 border-b pb-2">
        <Button
          variant={section === "skills" ? "default" : "ghost"}
          size="sm"
          onClick={() => setSection("skills")}
        >
          Skills &amp; Agents
        </Button>
        <Button
          variant={section === "templates" ? "default" : "ghost"}
          size="sm"
          onClick={() => setSection("templates")}
        >
          Prompt Templates
        </Button>
      </div>

      {section === "skills" && <SkillsSection projectId={projectId} />}
      {section === "templates" && <TemplatesSection projectId={projectId} />}
    </div>
  );
}
