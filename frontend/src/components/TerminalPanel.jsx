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

  // Keep ref in sync with latest prop
  useEffect(() => {
    onSessionEndRef.current = onSessionEnd;
  }, [onSessionEnd]);

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;

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
    term.open(containerRef.current);

    // Defer fit() until the browser has laid out the container,
    // otherwise xterm crashes reading dimensions of a 0-height element.
    requestAnimationFrame(() => {
      if (containerRef.current && containerRef.current.clientHeight > 0) {
        fitAddon.fit();
      }
    });

    terminalRef.current = term;
    fitAddonRef.current = fitAddon;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/terminals/${terminalId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        retryCountRef.current = 0;
        const dims = fitAddon.proposeDimensions();
        if (dims) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        term.write(event.data);
      };

      ws.onclose = (event) => {
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          if (onSessionEndRef.current) onSessionEndRef.current();
          return;
        }
        setStatus("disconnected");
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;
          setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {};
    }

    connect();

    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      if (!containerRef.current || containerRef.current.clientHeight === 0) return;
      fitAddon.fit();
      const dims = fitAddon.proposeDimensions();
      if (dims && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      wsRef.current?.close();
      term.dispose();
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
