import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Card, CardContent, CardFooter, CardHeader } from "@/shared/components/ui/card";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { useAnswerQuestion } from "@/features/questions/hooks";
import type { Question } from "@/shared/types";

interface QuestionCardProps {
  question: Question;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  answered: { label: "Answered", className: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300" },
  timed_out: { label: "Timed Out", className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400" },
};

export function QuestionCard({ question }: QuestionCardProps) {
  const [freeText, setFreeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const answerMutation = useAnswerQuestion();

  const isAnswered = question.status !== "pending";
  const statusCfg = statusConfig[question.status];

  const handleSubmit = () => {
    const answer = selectedOption || freeText;
    if (!answer.trim()) return;
    answerMutation.mutate({
      questionId: question.id,
      data: { answer, selected_option: selectedOption },
    });
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg.className}`}>
            {statusCfg.label}
          </span>
          {question.project_name && (
            <span className="text-xs text-muted-foreground">{question.project_name}</span>
          )}
        </div>
        {question.issue_name && (
          <Link
            to="/projects/$projectId/issues/$issueId"
            params={{ projectId: question.project_id, issueId: question.issue_id }}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Issue: {question.issue_name}
          </Link>
        )}
        <div className="text-xs text-muted-foreground">
          {question.created_at && (
            <span>Asked {formatDistanceToNow(new Date(question.created_at + "Z"), { addSuffix: true })}</span>
          )}
          {question.answered_at && question.status !== "pending" && (
            <span> &middot; Answered {formatDistanceToNow(new Date(question.answered_at + "Z"), { addSuffix: true })}</span>
          )}
        </div>
        <MarkdownViewer content={question.question} />
      </CardHeader>
      <CardContent className="space-y-3">
        {question.options && question.options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {question.options.map((opt) => (
              <Button
                key={opt}
                variant={selectedOption === opt ? "default" : "outline"}
                size="sm"
                disabled={isAnswered}
                onClick={() => setSelectedOption(opt)}
              >
                {opt}
              </Button>
            ))}
          </div>
        )}
        <Textarea
          placeholder="Or write your own answer..."
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          disabled={isAnswered}
          rows={2}
        />
      </CardContent>
      {!isAnswered && (
        <CardFooter className="justify-end">
          <Button
            size="sm"
            disabled={(!selectedOption && !freeText.trim()) || answerMutation.isPending}
            onClick={handleSubmit}
          >
            {answerMutation.isPending ? "Sending..." : "Answer"}
          </Button>
        </CardFooter>
      )}
      {isAnswered && question.answer && (
        <CardFooter>
          <p className="text-sm text-muted-foreground">
            Answered: {question.answer}
            {question.selected_option && ` (selected: ${question.selected_option})`}
          </p>
        </CardFooter>
      )}
    </Card>
  );
}
