import { useCallback, useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { SearchAddon } from "@xterm/addon-search";
import { Copy, Download, Search, X } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { TERMINAL_THEMES } from "@/features/terminals/themes";
import { useSettings } from "@/features/settings/hooks";
import "xterm/css/xterm.css";

interface TerminalPanelProps {
  terminalId: string;
  onSessionEnd?: () => void;
  onDownloadRecording?: () => void;
}

export function TerminalPanel({ terminalId, onSessionEnd, onDownloadRecording }: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onSessionEndRef = useRef(onSessionEnd);
  const cleanedUpRef = useRef(false);
  const searchAddonRef = useRef<SearchAddon | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "ended">("connecting");
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 5;

  const { data: settingsList } = useSettings();
  const themeName = settingsList?.find((s) => s.key === "terminal_theme")?.value ?? "catppuccin";
  const termTheme = TERMINAL_THEMES[themeName] ?? TERMINAL_THEMES.catppuccin;

  useEffect(() => {
    onSessionEndRef.current = onSessionEnd;
  }, [onSessionEnd]);

  const handleCopy = useCallback(() => {
    if (!termRef.current) return;
    const selection = termRef.current.getSelection();
    if (selection) {
      navigator.clipboard.writeText(selection).catch(() => {});
    }
  }, []);

  const handleSearch = useCallback((query: string, direction: "next" | "prev" = "next") => {
    if (!searchAddonRef.current || !query) return;
    if (direction === "next") {
      searchAddonRef.current.findNext(query, { incremental: false });
    } else {
      searchAddonRef.current.findPrevious(query);
    }
  }, []);

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;
    cleanedUpRef.current = false;

    const container = containerRef.current;
    container.innerHTML = "";

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Consolas', monospace",
      theme: termTheme,
    });

    termRef.current = term;

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    const searchAddon = new SearchAddon();
    searchAddonRef.current = searchAddon;
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.loadAddon(searchAddon);

    let opened = false;

    function openIfReady() {
      if (opened || cleanedUpRef.current) return;
      if (container.clientHeight === 0 || container.clientWidth === 0) return;

      opened = true;
      try {
        term.open(container);
        fitAddon.fit();
      } catch {
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
        if (cleanedUpRef.current) {
          ws.close();
          return;
        }
        setStatus("connected");
        retryCountRef.current = 0;
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        if (!cleanedUpRef.current) term.write(event.data);
      };

      ws.onclose = (event) => {
        if (cleanedUpRef.current) return;
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          onSessionEndRef.current?.();
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

    term.attachCustomKeyEventHandler((e) => {
      if (e.ctrlKey && e.key === "f") {
        e.preventDefault();
        setShowSearch((prev) => !prev);
        return false;
      }
      return true;
    });

    const resizeObserver = new ResizeObserver(() => {
      if (cleanedUpRef.current) return;
      if (!opened) {
        openIfReady();
        return;
      }
      if (container.clientHeight === 0) return;
      try {
        fitAddon.fit();
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      } catch {
        // ignore fit errors during transitions
      }
    });
    resizeObserver.observe(container);

    openIfReady();

    return () => {
      cleanedUpRef.current = true;
      searchAddonRef.current = null;
      termRef.current = null;
      resizeObserver.disconnect();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      const termToDispose = term;
      setTimeout(() => {
        try {
          termToDispose.dispose();
        } catch {}
      }, 50);
    };
  }, [terminalId]);

  useEffect(() => {
    if (termRef.current) {
      termRef.current.options.theme = termTheme;
    }
  }, [termTheme]);

  return (
    <div className="flex flex-col h-full" style={{ background: termTheme.background }}>
      <div className="flex items-center justify-end gap-1 px-2 py-1 bg-zinc-900 border-b border-zinc-800">
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
          onClick={handleCopy}
          title="Copy selection"
        >
          <Copy className="size-3 mr-1" />
          Copy
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
          onClick={() => setShowSearch((p) => !p)}
          title="Search (Ctrl+F)"
        >
          <Search className="size-3" />
        </Button>
        {onDownloadRecording && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs text-zinc-400 hover:text-zinc-200 px-2"
            onClick={onDownloadRecording}
            title="Download session recording"
          >
            <Download className="size-3 mr-1" />
            Log
          </Button>
        )}
      </div>
      {status === "ended" && (
        <div className="px-3 py-2 bg-zinc-800 text-zinc-400 text-sm text-center">
          Terminal session ended
        </div>
      )}
      {status === "disconnected" && (
        <div className="px-3 py-2 bg-yellow-900 text-yellow-300 text-sm text-center">
          Reconnecting...
        </div>
      )}
      {showSearch && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 border-b border-zinc-700">
          <Search className="size-3.5 text-zinc-400 flex-shrink-0" />
          <Input
            autoFocus
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              handleSearch(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch(searchQuery, e.shiftKey ? "prev" : "next");
              if (e.key === "Escape") setShowSearch(false);
            }}
            placeholder="Search… (Enter next, Shift+Enter prev)"
            className="h-6 text-xs bg-zinc-900 border-zinc-600 text-zinc-200 flex-1"
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 text-zinc-400"
            onClick={() => setShowSearch(false)}
          >
            <X className="size-3" />
          </Button>
        </div>
      )}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
