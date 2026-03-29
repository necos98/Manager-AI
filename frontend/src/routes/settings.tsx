import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle } from "lucide-react";
import { useSettings, useResetAllSettings } from "@/features/settings/hooks";
import { SettingsForm } from "@/features/settings/components/settings-form";
import { TerminalCommandsEditor } from "@/features/terminals/components/terminal-commands-editor";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Skeleton } from "@/shared/components/ui/skeleton";
import type { Setting } from "@/shared/types";

const TABS = ["Server", "Tool Descriptions", "Response Messages", "Terminal", "Claude", "Preferences"] as const;
type SettingsTab = (typeof TABS)[number];

function getCategory(key: string): string {
  if (key.startsWith("server.")) return "Server";
  if (key.endsWith(".description")) return "Tool Descriptions";
  if (key.endsWith(".response_message")) return "Response Messages";
  if (key.startsWith("claude.") || key === "ask_brainstorm_command") return "Claude";
  return "Other";
}

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function PreferencesPanel() {
  const [soundEnabled, setSoundEnabled] = useState(
    () => localStorage.getItem("manager_ai_sound") !== "false"
  );

  function handleToggleSound(enabled: boolean) {
    setSoundEnabled(enabled);
    localStorage.setItem("manager_ai_sound", enabled ? "true" : "false");
  }

  return (
    <div className="space-y-4">
      <div className="border rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="font-medium text-sm">Sound Notifications</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Play a sound when events arrive
          </p>
        </div>
        <button
          role="switch"
          aria-checked={soundEnabled}
          onClick={() => handleToggleSound(!soundEnabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            soundEnabled ? "bg-primary" : "bg-input"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              soundEnabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );
}

function SettingsPage() {
  const { data: settings, isLoading, error } = useSettings();
  const resetAll = useResetAllSettings();
  const [activeTab, setActiveTab] = useState<SettingsTab>("Server");
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-96" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">{error.message}</p>
      </div>
    );
  }

  const filteredSettings = (settings ?? []).filter(
    (s: Setting) => getCategory(s.key) === activeTab,
  );

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-6">Settings</h1>

      <div className="flex gap-1.5 mb-6">
        {TABS.map((tab) => (
          <Button
            key={tab}
            variant={activeTab === tab ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab(tab)}
            className="text-xs"
          >
            {tab}
          </Button>
        ))}
      </div>

      {activeTab === "Server" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 flex items-start gap-2">
          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
          Server name changes take effect after restarting the backend.
        </div>
      )}
      {activeTab === "Tool Descriptions" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 flex items-start gap-2">
          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
          Tool description changes take effect after restarting the backend.
        </div>
      )}

      {activeTab === "Terminal" ? (
        <div>
          <div className="mb-5 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
            These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands.
          </div>
          <TerminalCommandsEditor projectId={null} />
        </div>
      ) : activeTab === "Preferences" ? (
        <PreferencesPanel />
      ) : (
        <SettingsForm settings={filteredSettings} />
      )}

      {activeTab !== "Terminal" && activeTab !== "Preferences" && (
        <div className="mt-8 pt-6 border-t">
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => setShowResetConfirm(true)}
          >
            Reset all to defaults
          </Button>
        </div>
      )}

      <Dialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset All Settings?</DialogTitle>
            <DialogDescription>
              This will reset all settings to their default values. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResetConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => resetAll.mutate(undefined, { onSuccess: () => setShowResetConfirm(false) })}
              disabled={resetAll.isPending}
            >
              {resetAll.isPending ? "Resetting..." : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
