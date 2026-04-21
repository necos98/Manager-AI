import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

interface TerminalEntry {
  projectId: string;
  send: (text: string) => boolean;
}

interface TerminalContextValue {
  activeTerminalId: string | null;
  activeProjectId: string | null;
  setActive: (terminalId: string, projectId: string) => void;
  clearActive: (terminalId: string) => void;
  registerTerminal: (terminalId: string, entry: TerminalEntry) => void;
  unregisterTerminal: (terminalId: string) => void;
  injectIntoTerminal: (terminalId: string, text: string) => boolean;
  getProjectIdFor: (terminalId: string) => string | null;
}

const TerminalContext = createContext<TerminalContextValue | null>(null);

export function TerminalProvider({ children }: { children: React.ReactNode }) {
  const [activeTerminalId, setActiveTerminalId] = useState<string | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const registryRef = useRef<Map<string, TerminalEntry>>(new Map());

  const setActive = useCallback((terminalId: string, projectId: string) => {
    setActiveTerminalId(terminalId);
    setActiveProjectId(projectId);
  }, []);

  const clearActive = useCallback((terminalId: string) => {
    setActiveTerminalId((curr) => {
      if (curr === terminalId) {
        setActiveProjectId(null);
        return null;
      }
      return curr;
    });
  }, []);

  const registerTerminal = useCallback((terminalId: string, entry: TerminalEntry) => {
    registryRef.current.set(terminalId, entry);
  }, []);

  const unregisterTerminal = useCallback((terminalId: string) => {
    registryRef.current.delete(terminalId);
  }, []);

  const injectIntoTerminal = useCallback((terminalId: string, text: string) => {
    const entry = registryRef.current.get(terminalId);
    if (!entry) return false;
    return entry.send(text);
  }, []);

  const getProjectIdFor = useCallback((terminalId: string) => {
    return registryRef.current.get(terminalId)?.projectId ?? null;
  }, []);

  const value = useMemo<TerminalContextValue>(
    () => ({
      activeTerminalId,
      activeProjectId,
      setActive,
      clearActive,
      registerTerminal,
      unregisterTerminal,
      injectIntoTerminal,
      getProjectIdFor,
    }),
    [activeTerminalId, activeProjectId, setActive, clearActive, registerTerminal, unregisterTerminal, injectIntoTerminal, getProjectIdFor],
  );

  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}

export function useTerminalContext(): TerminalContextValue {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminalContext must be used within TerminalProvider");
  return ctx;
}
