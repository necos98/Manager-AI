import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { queryClient } from "@/shared/lib/query-client";

interface EventContextValue {}

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

function showTypedToast(
  eventType: string | undefined,
  title: string,
  description: string,
  action?: { label: string; onClick: () => void }
) {
  const opts = { description, action };
  if (eventType === "hook_failed") {
    toast.error(title, opts);
  } else if (eventType === "hook_completed") {
    toast.success(title, opts);
  } else if (eventType === "notification") {
    toast.info(title, opts);
  } else if (eventType === "hook_started") {
    toast(title, { ...opts, duration: 2000 });
  } else {
    toast(title, opts);
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
        const issueName = data.issue_name as string | undefined;
        const eventType = data.type as string | undefined;
        const message =
          (data.message as string) || (data.status as string) || "New event";
        const title = issueName || eventType || "Event";

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

        showTypedToast(eventType, title, message, action);
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
