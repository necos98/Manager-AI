import { useState } from "react";
import { MessageSquare, Send, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { useFeedback, useAddFeedback } from "@/features/issues/hooks";

interface PlanFeedbackProps {
  projectId: string;
  issueId: string;
}

export function PlanFeedback({ projectId, issueId }: PlanFeedbackProps) {
  const [text, setText] = useState("");
  const { data: feedbacks = [] } = useFeedback(projectId, issueId);
  const addFeedback = useAddFeedback(projectId, issueId);

  const handleSubmit = () => {
    if (!text.trim()) return;
    addFeedback.mutate(
      { content: text.trim() },
      { onSuccess: () => setText("") }
    );
  };

  return (
    <div className="space-y-4 mt-4 border-t pt-4">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <MessageSquare className="size-4" />
        Feedback for Claude
      </div>

      {feedbacks.length > 0 && (
        <div className="space-y-2">
          {feedbacks.map((fb) => (
            <div key={fb.id} className="rounded-md bg-muted px-3 py-2 text-sm">
              <p className="whitespace-pre-wrap">{fb.content}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {new Date(fb.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <Textarea
          placeholder="Give Claude feedback on the plan (e.g. add tests for X, consider Y)..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          className="flex-1"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSubmit();
          }}
        />
        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={!text.trim() || addFeedback.isPending}
          className="self-end"
        >
          {addFeedback.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Send className="size-4" />
          )}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">Ctrl+Enter to send</p>
    </div>
  );
}
