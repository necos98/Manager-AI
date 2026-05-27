import { useState, useRef, useEffect } from "react";
import { Send, Loader2, MessageSquare } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Skeleton } from "@/shared/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { usePipelineRuns, usePipelineMessages, useSendPipelineMessage } from "@/features/pipeline-runs/hooks";

interface AgentChatProps {
  projectId: string;
  issueId: string;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const AGENT_COLORS = [
  "text-blue-400",
  "text-green-400",
  "text-purple-400",
  "text-orange-400",
  "text-pink-400",
  "text-teal-400",
];

function agentColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AGENT_COLORS[Math.abs(hash) % AGENT_COLORS.length];
}

export function AgentChat({ projectId, issueId }: AgentChatProps) {
  const { data: runs } = usePipelineRuns(projectId, issueId);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [message, setMessage] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const selectedRun = runs?.find((r) => r.id === selectedRunId) ?? runs?.[0] ?? null;
  const isRunActive = selectedRun?.status === "RUNNING";

  const { data: messages, isLoading: messagesLoading } = usePipelineMessages(
    projectId,
    selectedRun?.id ?? "",
    { refetchInterval: isRunActive ? 3000 : false }
  );

  const sendMessage = useSendPipelineMessage(projectId);

  // Auto-select first run
  useEffect(() => {
    if (!selectedRunId && runs && runs.length > 0) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!message.trim() || !selectedRun || sendMessage.isPending) return;
    sendMessage.mutate(
      {
        runId: selectedRun.id,
        data: { sender_agent_name: "User", content: message.trim() },
      },
      { onSuccess: () => setMessage("") }
    );
  };

  if (!runs || runs.length === 0) return null;

  return (
    <div className="flex flex-col h-full min-h-[400px]">
      {/* Run selector header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
        <Select value={selectedRunId} onValueChange={setSelectedRunId}>
          <SelectTrigger className="h-8 w-64 text-xs">
            <SelectValue placeholder="Select pipeline run..." />
          </SelectTrigger>
          <SelectContent>
            {runs.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                Pipeline {r.id.slice(0, 8)} — {r.status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isRunActive && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="size-3 animate-spin" />
            Live
          </span>
        )}
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 min-h-0">
        <div ref={scrollRef} className="p-4 space-y-3">
          {messagesLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))
          ) : !messages || messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-muted-foreground">
              <MessageSquare className="size-8 mb-2 opacity-40" />
              <p className="text-sm">No messages yet</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${agentColor(msg.sender_agent_name)}`}>
                    {msg.sender_agent_name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {timeAgo(msg.created_at)}
                  </span>
                </div>
                <div className="pl-0 text-sm prose prose-sm dark:prose-invert max-w-none">
                  <MarkdownViewer content={msg.content} />
                </div>
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      {selectedRun && (
        <div className="px-4 py-3 border-t shrink-0">
          <div className="flex items-end gap-2">
            <Textarea
              placeholder={isRunActive ? "Type a message..." : "Run completed. Messages are read-only."}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={2}
              className="min-h-0 resize-none text-sm"
              disabled={sendMessage.isPending}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <Button
              size="icon"
              className="shrink-0"
              onClick={handleSend}
              disabled={!message.trim() || sendMessage.isPending}
            >
              {sendMessage.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
