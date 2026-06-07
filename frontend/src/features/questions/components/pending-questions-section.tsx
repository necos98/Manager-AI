import { QuestionCard } from "./question-card";
import type { Question } from "@/shared/types";

interface PendingQuestionsSectionProps {
  pendingQuestions?: Question[];
}

export function PendingQuestionsSection({ pendingQuestions }: PendingQuestionsSectionProps) {
  if (!pendingQuestions || pendingQuestions.length === 0) return null;
  return (
    <div className="border-t mt-6 pt-6 px-4">
      <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
      <div className="space-y-3">
        {pendingQuestions.map((q) => (
          <QuestionCard key={q.id} question={q} />
        ))}
      </div>
    </div>
  );
}
