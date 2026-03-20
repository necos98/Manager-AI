import { useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "xterm/css/xterm.css";

export default function TerminalPanel({ terminalId, onSessionEnd }) {
  const containerRef = useRef(null);
  const terminalRef = useRef(null);
  const wsRef = useRef(null);
  const fitAddonRef = useRef(null);
  const onSessionEndRef = useRef(onSessionEnd);
  const [status, setStatus] = useState("connecting");
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 5;
  const cleanedUpRef = useRef(false);

  useEffect(() => {
    onSessionEndRef.current = onSessionEnd;
  }, [onSessionEnd]);

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;
    cleanedUpRef.current = false;

    const container = containerRef.current;

    // Clear any leftover DOM from a previous xterm instance
    // (React StrictMode disposes then re-creates)
    container.innerHTML = "";

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Consolas', monospace",
      theme: {
        background: "#0d0d0d",
        foreground: "#cdd6f4",
        cursor: "#89b4fa",
      },
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    terminalRef.current = term;
    fitAddonRef.current = fitAddon;

    // Only open xterm once the container has real dimensions.
    // open() creates a Viewport that reads dimensions synchronously;
    // if height is 0 it crashes.
    let opened = false;

    function openIfReady() {
      if (opened || cleanedUpRef.current) return;
      if (container.clientHeight === 0 || container.clientWidth === 0) return;

      opened = true;
      try {
        term.open(container);
        fitAddon.fit();
      } catch (e) {
        console.warn("xterm open/fit error:", e);
        return;
      }
      connectWs();
    }

    function connectWs() {
      if (cleanedUpRef.current) return;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/terminals/${terminalId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cleanedUpRef.current) { ws.close(); return; }
        setStatus("connected");
        retryCountRef.current = 0;
        const dims = fitAddon.proposeDimensions();
        if (dims && dims.cols && dims.rows) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        if (term && !cleanedUpRef.current) term.write(event.data);
      };

      ws.onclose = (event) => {
        if (cleanedUpRef.current) return;
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          if (onSessionEndRef.current) onSessionEndRef.current();
          return;
        }
        setStatus("disconnected");
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;
          setTimeout(connectWs, delay);
        }
      };

      ws.onerror = () => {};
    }

    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      if (cleanedUpRef.current) return;
      // If not yet opened, try now that we have dimensions
      if (!opened) { openIfReady(); return; }
      if (container.clientHeight === 0) return;
      try {
        fitAddon.fit();
        const dims = fitAddon.proposeDimensions();
        if (dims && dims.cols && dims.rows && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      } catch {
        // ignore fit errors during transitions
      }
    });
    resizeObserver.observe(container);

    // Try to open immediately if container already has dimensions
    openIfReady();

    return () => {
      cleanedUpRef.current = true;
      resizeObserver.disconnect();
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect attempts
        wsRef.current.close();
      }
      // Defer dispose to avoid interfering with xterm's internal setTimeout callbacks
      const termToDispose = term;
      setTimeout(() => {
        try { termToDispose.dispose(); } catch {}
      }, 50);
    };
  }, [terminalId]);

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d]">
      {status === "ended" && (
        <div className="px-3 py-2 bg-gray-800 text-gray-400 text-sm text-center">
          Terminal session ended
        </div>
      )}
      {status === "disconnected" && (
        <div className="px-3 py-2 bg-yellow-900 text-yellow-300 text-sm text-center">
          Reconnecting...
        </div>
      )}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
