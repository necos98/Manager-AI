import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { queryClient } from "@/shared/lib/query-client";

export type WsEventData = Record<string, unknown> & {
  type?: string;
  project_id?: string;
  issue_id?: string;
  issue_name?: string;
  message?: string;
  error?: string;
  hook_name?: string;
  hook_description?: string;
  new_status?: string;
  content_type?: string;
  title?: string;
  source_type?: string;
};

type EventSubscriber = (event: WsEventData) => void;

interface EventContextValue {
  subscribe: (fn: EventSubscriber) => () => void;
}

const EventContext = createContext<EventContextValue | null>(null);

const notificationAudio = new Audio("/sounds/notification.wav");
notificationAudio.volume = 0.5;

function unlockAudio() {
  notificationAudio
    .play()
    .then(() => {
      notificationAudio.pause();
      notificationAudio.currentTime = 0;
    })
    .catch(() => {});
  document.removeEventListener("click", unlockAudio);
  document.removeEventListener("keydown", unlockAudio);
}
document.addEventListener("click", unlockAudio);
document.addEventListener("keydown", unlockAudio);

function isSoundEnabled(): boolean {
  return localStorage.getItem("manager_ai_sound") !== "false";
}

function playNotificationSound() {
  if (!isSoundEnabled()) return;
  try {
    notificationAudio.currentTime = 0;
    notificationAudio.play().catch(() => {});
  } catch {
    // Audio API unavailable
  }
}

const STATUS_LABELS: Record<string, string> = {
  New: "New",
  Reasoning: "Analyzing",
  Planned: "Planned",
  Accepted: "Accepted",
  Finished: "Finished",
  Canceled: "Canceled",
};

const CONTENT_TYPE_LABELS: Record<string, string> = {
  specification: "Specification written",
  plan: "Plan written",
  name: "Name updated",
  recap: "Recap written",
};

interface ToastContent {
  title: string;
  message: string;
  variant: "default" | "success" | "error" | "info";
  duration?: number;
  silent?: boolean;
}

function buildToastContent(data: WsEventData): ToastContent {
  const issueName = data.issue_name || "";
  const hookLabel = data.hook_description || data.hook_name || "Operazione";

  switch (data.type) {
    case "hook_started":
      return {
        title: hookLabel,
        message: issueName,
        variant: "default",
        duration: 3000,
      };

    case "hook_completed":
      return {
        title: hookLabel,
        message: issueName || "Completed",
        variant: "success",
      };

    case "hook_failed":
      return {
        title: hookLabel,
        message: data.error || "Unknown error",
        variant: "error",
      };

    case "issue_status_changed": {
      const statusLabel = STATUS_LABELS[data.new_status as string] ?? data.new_status ?? "aggiornata";
      return {
        title: issueName || "Issue",
        message: `Status → ${statusLabel}`,
        variant: "default",
      };
    }

    case "issue_content_updated": {
      const contentLabel = CONTENT_TYPE_LABELS[data.content_type as string] ?? `${data.content_type} updated`;
      return {
        title: issueName || "Issue",
        message: contentLabel,
        variant: "default",
      };
    }

    case "notification":
      return {
        title: (data.title as string) || "Notifica",
        message: (data.message as string) || "",
        variant: "info",
      };

    case "task_updated":
      return { title: "", message: "", variant: "default", silent: true };

    case "embedding_completed":
      return {
        title: "Indexing complete",
        message: (data.title as string) || (data.source_type as string) || "",
        variant: "default",
        duration: 2500,
      };

    case "embedding_failed":
      return {
        title: "Indexing failed",
        message: `${data.title ?? ""}: ${data.error ?? "unknown error"}`.replace(/^: /, ""),
        variant: "error",
      };

    case "terminal_created":
      return {
        title: "Analysis started",
        message: (data.issue_name as string) || "Terminal open",
        variant: "default",
        duration: 3000,
      };

    case "embedding_skipped":
    case "project_updated":
      return { title: "", message: "", variant: "default", silent: true };

    default:
      return {
        title: (data.title as string) || data.type || "Evento",
        message: (data.message as string) || "",
        variant: "default",
      };
  }
}

function showToast(content: ToastContent, action?: { label: string; onClick: () => void }) {
  if (content.silent) return;
  const opts = { description: content.message || undefined, action, duration: content.duration };
  if (content.variant === "error") toast.error(content.title, opts);
  else if (content.variant === "success") toast.success(content.title, opts);
  else if (content.variant === "info") toast.info(content.title, opts);
  else toast(content.title, opts);
}

export function EventProvider({ children }: { children: React.ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const backoffRef = useRef(1000);
  const cleanedUpRef = useRef(false);
  const navigate = useNavigate();
  const subscribersRef = useRef<Set<EventSubscriber>>(new Set());

  const subscribe = useCallback((fn: EventSubscriber) => {
    subscribersRef.current.add(fn);
    return () => {
      subscribersRef.current.delete(fn);
    };
  }, []);

  const connect = useCallback(() => {
    if (cleanedUpRef.current) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/events/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cleanedUpRef.current) {
        ws.close();
        return;
      }
      backoffRef.current = 1000;
    };

    ws.onmessage = (event) => {
      if (cleanedUpRef.current) return;
      try {
        const data = JSON.parse(event.data) as WsEventData;

        // Notify all subscribers
        subscribersRef.current.forEach((fn) => fn(data));
        const projectId = data.project_id;
        const issueId = data.issue_id;

        const action =
          projectId && issueId
            ? {
                label: "View",
                onClick: () => {
                  navigate({
                    to: "/projects/$projectId/issues/$issueId",
                    params: { projectId, issueId },
                  });
                },
              }
            : undefined;

        const toastContent = buildToastContent(data);
        showToast(toastContent, action);
        if (!toastContent.silent) playNotificationSound();

        // Invalidate terminal queries when a new terminal is spawned
        if (data.type === "terminal_created") {
          queryClient.invalidateQueries({ queryKey: ["terminals"] });
        }

        // Invalidate relevant queries for real-time updates
        if (projectId && issueId) {
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId, "issues", issueId],
          });
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId, "issues"],
          });
        } else if (projectId) {
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId],
          });
        }
      } catch {
        // Ignore unparseable messages
      }
    };

    ws.onclose = () => {
      if (cleanedUpRef.current) return;
      const delay = Math.min(backoffRef.current, 30000);
      backoffRef.current = Math.min(backoffRef.current * 2, 30000);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [navigate]);

  useEffect(() => {
    cleanedUpRef.current = false;
    connect();

    return () => {
      cleanedUpRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        }
        wsRef.current = null;
      }
    };
  }, [connect]);

  return (
    <EventContext.Provider value={{ subscribe }}>
      {children}
    </EventContext.Provider>
  );
}

export function useEvents() {
  return useContext(EventContext);
}
