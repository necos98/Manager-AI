import { usePendingQuestions } from "@/features/questions/hooks";
import { QuestionCard } from "@/features/questions/components/question-card";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";

interface TerminalWithQuestionsProps {
  terminalId: string;
  projectId: string;
  issueId: string;
  hideQuestions?: boolean;
  readOnly?: boolean;
  onSessionEnd?: () => void;
  onDownloadRecording?: () => void;
}

export function TerminalWithQuestions({
  terminalId,
  projectId,
  issueId,
  hideQuestions,
  readOnly,
  onSessionEnd,
  onDownloadRecording,
}: TerminalWithQuestionsProps) {
  const { data: questions } = usePendingQuestions(projectId, issueId);

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 min-h-0">
        <TerminalPanel
          terminalId={terminalId}
          projectId={projectId}
          readOnly={readOnly}
          onSessionEnd={onSessionEnd}
          onDownloadRecording={onDownloadRecording}
        />
      </div>
      {!hideQuestions && questions && questions.length > 0 && (
        <div className="border-t mt-2 pt-3 px-3 flex-shrink-0 max-h-[40%] overflow-y-auto">
          <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
          <div className="space-y-3">
            {questions.map((q) => (
              <QuestionCard key={q.id} question={q} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
