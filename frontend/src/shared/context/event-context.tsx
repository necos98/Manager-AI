import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { queryClient } from "@/shared/lib/query-client";

interface EventContextValue {
  // Extensible if needed
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

function playNotificationSound() {
  try {
    notificationAudio.currentTime = 0;
    notificationAudio.play().catch(() => {});
  } catch {
    // Audio API unavailable
  }
}

function buildToast(data: Record<string, unknown>): { title: string; description: string } {
  const type = data.type as string;
  const issueName = (data.issue_name as string) || "";
  const projectName = (data.project_name as string) || "";
  const title = (data.title as string) || "";
  const message = (data.message as string) || "";
  const hookName = (data.hook_name as string) || "";
  const error = (data.error as string) || "";

  const prefix = projectName ? `${projectName} • ` : "";

  switch (type) {
    case "notification":
      return {
        title: issueName || "Notifica",
        description: `${prefix}${message}`,
      };
    case "hook_started":
      return {
        title: issueName || "Hook avviato",
        description: `${prefix}${hookName} in esecuzione…`,
      };
    case "hook_completed":
      return {
        title: issueName || "Hook completato",
        description: `${prefix}${hookName} completato`,
      };
    case "hook_failed":
      return {
        title: issueName || "Hook fallito",
        description: `${prefix}${error || "Errore sconosciuto"}`,
      };
    case "embedding_completed":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding completato`,
      };
    case "embedding_failed":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding fallito: ${error}`,
      };
    case "embedding_skipped":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding saltato`,
      };
    default:
      return {
        title: issueName || title || "Evento",
        description: `${prefix}${message || "New event"}`,
      };
  }
}

export function EventProvider({ children }: { children: React.ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const backoffRef = useRef(1000);
  const cleanedUpRef = useRef(false);
  const navigate = useNavigate();

  const connect = useCallback(() => {
    if (cleanedUpRef.current) return;

    const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/events/ws`;

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
        const data = JSON.parse(event.data) as Record<string, unknown>;
        const projectId = data.project_id as string | undefined;
        const issueId = data.issue_id as string | undefined;

        const { title, description } = buildToast(data);

        toast(title, {
          description,
          action:
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
              : undefined,
        });

        playNotificationSound();

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
    <EventContext.Provider value={{}}>
      {children}
    </EventContext.Provider>
  );
}

export function useEvents() {
  return useContext(EventContext);
}
