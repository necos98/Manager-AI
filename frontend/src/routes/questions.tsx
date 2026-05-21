import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { HelpCircle } from "lucide-react";
import { usePendingQuestions } from "@/features/questions/hooks";
import { useProjects } from "@/features/projects/hooks";
import { QuestionCard } from "@/features/questions/components/question-card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/shared/components/ui/collapsible";

export const Route = createFileRoute("/questions")({
  component: QuestionsPage,
});

function QuestionsPage() {
  const { data: questions, isLoading } = usePendingQuestions();
  const { data: projects } = useProjects();

  useEffect(() => {
    document.title = "Questions - Manager AI";
  }, []);

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2].map((i) => <Skeleton key={i} className="h-32" />)}
      </div>
    );
  }

  const grouped: Record<string, typeof questions> = {};
  for (const q of questions ?? []) {
    (grouped[q.project_id] ??= []).push(q);
  }

  const getProjectName = (projectId: string) =>
    projects?.find((p) => p.id === projectId)?.name ?? projectId;

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-xl font-semibold">Questions</h1>
        <span className="text-sm text-muted-foreground">
          {questions?.length ?? 0} pending
        </span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {Object.keys(grouped).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <HelpCircle className="size-10 mb-3" />
            <p>No pending questions</p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(grouped).map(([projectId, qs]) => (
              <Collapsible key={projectId} defaultOpen>
                <CollapsibleTrigger className="text-sm font-medium mb-2 flex items-center gap-1">
                  {getProjectName(projectId)}
                  <span className="text-xs text-muted-foreground">({qs?.length ?? 0})</span>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 pt-2">
                  {qs?.map((q) => <QuestionCard key={q.id} question={q} />)}
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
