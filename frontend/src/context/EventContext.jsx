import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ToastContainer from "../components/ToastContainer";

const EventContext = createContext(null);

function playNotificationSound() {
  try {
    const audio = new Audio("/sounds/notification.mp3");
    audio.volume = 0.5;
    audio.play().catch(() => {});
  } catch (e) {
    // Audio API unavailable or blocked — silently ignore
  }
}

export function EventProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const backoffRef = useRef(1000);
  const cleanedUpRef = useRef(false);
  const navigate = useNavigate();

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const connect = useCallback(() => {
    if (cleanedUpRef.current) return;

    const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/events/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cleanedUpRef.current) { ws.close(); return; }
      backoffRef.current = 1000;
    };

    ws.onmessage = (event) => {
      if (cleanedUpRef.current) return;
      try {
        const data = JSON.parse(event.data);
        const toast = {
          id: Date.now() + Math.random(),
          ...data,
        };
        setToasts((prev) => [toast, ...prev].slice(0, 5));
        playNotificationSound();
      } catch (e) {
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
  }, []);

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

  const handleToastClick = useCallback(
    (toast) => {
      if (toast.project_id && toast.issue_id) {
        navigate(`/projects/${toast.project_id}/issues/${toast.issue_id}`);
      }
      dismissToast(toast.id);
    },
    [navigate, dismissToast]
  );

  return (
    <EventContext.Provider value={{ toasts, dismissToast }}>
      {children}
      <ToastContainer
        toasts={toasts}
        onDismiss={dismissToast}
        onToastClick={handleToastClick}
      />
    </EventContext.Provider>
  );
}

export function useEvents() {
  return useContext(EventContext);
}
