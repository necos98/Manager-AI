import { useState } from "react";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Card, CardContent, CardFooter, CardHeader } from "@/shared/components/ui/card";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { useAnswerQuestion } from "@/features/questions/hooks";
import type { Question } from "@/shared/types";

interface QuestionCardProps {
  question: Question;
}

export function QuestionCard({ question }: QuestionCardProps) {
  const [freeText, setFreeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const answerMutation = useAnswerQuestion();

  const isAnswered = question.status !== "pending";

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
      <CardHeader>
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
