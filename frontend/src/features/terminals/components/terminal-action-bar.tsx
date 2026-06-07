import { Play, Square } from "lucide-react";
import { Button } from "@/shared/components/ui/button";

interface TerminalActionBarProps {
  hasAny: boolean;
  hasSplit: boolean;
  openTerminal: () => void;
  onRequestClose: () => void;
  isOpening: boolean;
}

export function TerminalActionBar({ hasAny, hasSplit, openTerminal, onRequestClose, isOpening }: TerminalActionBarProps) {
  return (
    <div className="flex items-center justify-end gap-2 px-6 py-2 border-b flex-shrink-0">
      {!hasAny && (
        <Button size="sm" onClick={openTerminal} disabled={isOpening}>
          <Play className="size-3 mr-1" />
          {isOpening ? "Opening..." : "Open Terminal"}
        </Button>
      )}
      {hasAny && !hasSplit && (
        <Button variant="destructive" size="sm" onClick={onRequestClose}>
          <Square className="size-3 mr-1" />
          Close Terminal
        </Button>
      )}
      {hasSplit && (
        <Button variant="destructive" size="sm" onClick={onRequestClose}>
          <Square className="size-3 mr-1" />
          Close All
        </Button>
      )}
    </div>
  );
}
