import { Button } from "@/shared/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/shared/components/ui/dialog";

interface TerminalDialogsProps {
  showLimitWarning: boolean;
  setShowLimitWarning: (v: boolean) => void;
  openAnyway: () => void;
  showCloseConfirm: boolean;
  setShowCloseConfirm: (v: boolean) => void;
  closeAll: () => void;
  hasSplit: boolean;
}

export function TerminalDialogs({
  showLimitWarning, setShowLimitWarning, openAnyway,
  showCloseConfirm, setShowCloseConfirm, closeAll, hasSplit,
}: TerminalDialogsProps) {
  return (
    <>
      <Dialog open={showLimitWarning} onOpenChange={setShowLimitWarning}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminal Limit Reached</DialogTitle>
            <DialogDescription>
              You have reached the soft limit of open terminals. Consider closing unused terminals.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLimitWarning(false)}>Cancel</Button>
            <Button onClick={openAnyway}>Open Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Terminal{hasSplit ? "s" : ""}?</DialogTitle>
            <DialogDescription>
              This will kill the terminal process{hasSplit ? "es" : ""}. Any running commands will be terminated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloseConfirm(false)}>Cancel</Button>
            <Button variant="destructive" onClick={closeAll}>
              Close {hasSplit ? "All" : "Terminal"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
