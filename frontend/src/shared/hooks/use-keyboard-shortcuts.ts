import { useState, useEffect, useCallback } from "react";

interface ShortcutCallbacks {
  onCmdPalette: () => void;
  onNewIssue: () => void;
  onNavigate: (path: string) => void;
  onSearchFocus: () => void;
  onHelp: () => void;
}

/**
 * Global keyboard shortcuts hook.
 *
 * Implements Vim/Linear-style sequences:
 * - Cmd+K / Ctrl+K → open command palette
 * - g i → go to issues page
 * - g d → go to dashboard
 * - g p → go to projects page
 * - n → new issue (when no input is focused)
 * - / → focus search (when no input is focused)
 * - ? → show help overlay
 */
export function useKeyboardShortcuts(callbacks: ShortcutCallbacks) {
  const [gPressed, setGPressed] = useState(false);

  useEffect(() => {
    let gTimeout: ReturnType<typeof setTimeout> | null = null;

    const isInputFocused = (): boolean => {
      const tag = document.activeElement?.tagName?.toLowerCase();
      return (
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        (document.activeElement?.getAttribute("role") === "textbox") ||
        document.activeElement?.isContentEditable === true ||
        // Don't intercept inside command palette
        document.activeElement?.closest("[data-command-palette]") !== null
      );
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      // ── Cmd+K / Ctrl+K (always works) ──
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        e.stopPropagation();
        setGPressed(false);
        callbacks.onCmdPalette();
        return;
      }

      // Don't process other shortcuts when typing in inputs
      if (isInputFocused()) return;

      // ── ? → help ──
      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setGPressed(false);
        callbacks.onHelp();
        return;
      }

      // ── / → search focus ──
      if (e.key === "/" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setGPressed(false);
        callbacks.onSearchFocus();
        return;
      }

      // ── n → new issue ──
      if (e.key === "n" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setGPressed(false);
        callbacks.onNewIssue();
        return;
      }

      // ── g sequence ──
      if (e.key === "g" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setGPressed(true);
        if (gTimeout) clearTimeout(gTimeout);
        gTimeout = setTimeout(() => {
          setGPressed(false);
        }, 1000); // 1s timeout for the sequence
        return;
      }

      // Handle second key in g sequence
      if (gPressed) {
        if (e.key === "i") {
          e.preventDefault();
          setGPressed(false);
          if (gTimeout) clearTimeout(gTimeout);
          callbacks.onNavigate("/issues");
          return;
        }
        if (e.key === "d") {
          e.preventDefault();
          setGPressed(false);
          if (gTimeout) clearTimeout(gTimeout);
          callbacks.onNavigate("/");
          return;
        }
        if (e.key === "p") {
          e.preventDefault();
          setGPressed(false);
          if (gTimeout) clearTimeout(gTimeout);
          callbacks.onNavigate("/projects");
          return;
        }
        // Reset if second key doesn't match
        setGPressed(false);
        if (gTimeout) clearTimeout(gTimeout);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (gTimeout) clearTimeout(gTimeout);
    };
  }, [callbacks, gPressed]);

  // Expose gPressed state so UI can show the "waiting for key" indicator
  return { gPressed };
}
