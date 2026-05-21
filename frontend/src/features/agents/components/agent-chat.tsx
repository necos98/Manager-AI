import { useEffect, useRef, useState } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { useEvents } from "@/shared/context/event-context";

interface ChatMessage {
  id: string;
  agent_name: string;
  agent_role: string;
  content: string;
  message_type: string;
  created_at: string;
}

interface AgentChatProps {
  issueId: string;
}

const ROLE_COLORS: Record<string, string> = {
  architect: "border-l-purple-500",
  developer: "border-l-blue-500",
  reviewer: "border-l-emerald-500",
  qa: "border-l-orange-500",
};

const ROLE_DOT_COLORS: Record<string, string> = {
  architect: "bg-purple-500",
  developer: "bg-blue-500",
  reviewer: "bg-emerald-500",
  qa: "bg-orange-500",
};

const TYPE_LABELS: Record<string, string> = {
  context: "Context",
  decision: "Decision",
  question: "Question",
  answer: "Answer",
  status: "Status",
};

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function AgentChat({ issueId }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const events = useEvents();

  useEffect(() => {
    if (!events) return;
    return events.subscribe((data) => {
      if (data.type === "agent_message_added" && data.issue_id === issueId) {
        const msg = data.message as unknown as ChatMessage;
        if (msg) {
          setMessages((prev) => [...prev, msg]);
        }
      }
    });
  }, [events, issueId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center py-8">
            No agent activity yet. Agents will post messages here as they work.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <div ref={scrollRef} className="max-h-[500px] overflow-y-auto space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`rounded-lg border p-3 text-sm border-l-[3px] ${ROLE_COLORS[msg.agent_role] || "border-l-gray-500"}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`size-2.5 rounded-full shrink-0 ${ROLE_DOT_COLORS[msg.agent_role] || "bg-gray-500"}`}
                />
                <span className="font-medium">{msg.agent_name}</span>
                <span className="text-xs text-muted-foreground">{msg.agent_role}</span>
                <span className="text-xs text-muted-foreground ml-auto">{timeAgo(msg.created_at)}</span>
              </div>
              <div className="whitespace-pre-wrap text-xs font-mono mt-1">{msg.content}</div>
              <div className="mt-1">
                <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded">
                  {TYPE_LABELS[msg.message_type] || msg.message_type}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
