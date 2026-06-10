import { useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Loader2, Bot, BookOpen, Play, Terminal, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { useSettings, useUpdateSetting, useResetAllSettings, useInstallHermesMcp, useInstallHermesSkills, useHermesCommands } from "@/features/settings/hooks";
import { SettingsForm } from "@/features/settings/components/settings-form";
import { TerminalCommandsEditor } from "@/features/terminals/components/terminal-commands-editor";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { useCreateHermesTerminal, useKillTerminal } from "@/features/terminals/hooks";
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

const TABS = ["Server", "Tool Descriptions", "Response Messages", "Terminal", "Agent CLI", "Hermes", "Preferences", "Telegram"] as const;
type SettingsTab = (typeof TABS)[number];

function getCategory(key: string): string {
  if (key.startsWith("server.")) return "Server";
  if (key.endsWith(".description")) return "Tool Descriptions";
  if (key.endsWith(".response_message")) return "Response Messages";
  if (key === "agent_provider") return "_hidden";
  if (key.startsWith("claude.") || key === "ask_brainstorm_command") return "Agent CLI";
  if (key.startsWith("telegram.")) return "Telegram";
  return "Other";
}

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});


function HermesIntegrationPanel() {
  const installMcp = useInstallHermesMcp();
  const installSkills = useInstallHermesSkills();

  return (
    <div className="border rounded-lg p-4 mt-5 space-y-4">
      {/* MCP install row */}
      <div className="flex items-start gap-3">
        <Bot className="size-5 mt-0.5 text-primary" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">Connessione MCP</p>
          <p className="text-xs text-muted-foreground mt-1">
            Connect Hermes Agent to the Manager AI MCP server. This allows
            Hermes to directly manage issues, pipelines, memories, and more
            through the Manager AI backend.
          </p>
          <div className="mt-3">
            <div className="flex items-center gap-3 mb-2">
              <Button
                size="sm"
                onClick={() => installMcp.mutate()}
                disabled={installMcp.isPending}
              >
                {installMcp.isPending ? (
                  <>
                    <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  "Genera comando MCP"
                )}
              </Button>
            </div>
            {installMcp.data?.commands && installMcp.data.commands.length > 0 && (
              <div className="bg-muted rounded-md border">
                <div className="flex items-center justify-between px-3 py-2 border-b">
                  <span className="text-xs font-medium text-muted-foreground">
                    Esegui nel terminale del tuo progetto:
                  </span>
                </div>
                {installMcp.data.commands.map((cmd, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2 border-b last:border-b-0">
                    <pre className="flex-1 text-sm font-mono overflow-x-auto whitespace-pre-wrap break-all mr-2">
                      {cmd}
                    </pre>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs shrink-0"
                      onClick={() => {
                        navigator.clipboard.writeText(cmd);
                        toast.success("📋 Copiato!");
                      }}
                    >
                      Copia
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
          {installMcp.isError && (
            <p className="mt-2 text-xs text-destructive">
              {installMcp.error?.message ?? "Errore di connessione"}
            </p>
          )}
        </div>
      </div>

      {/* Skills install row */}
      <div className="flex items-start gap-3 pt-3 border-t">
        <BookOpen className="size-5 mt-0.5 text-primary" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">Skill di Orchestrazione</p>
          <p className="text-xs text-muted-foreground mt-1">
            Installa le skill in Hermes per abilitare orchestrazione e
            auto-mode. Include manager-ai-orchestrator, manager-ai-issue-worker,
            run-issue, run-pipeline, ask-and-brainstorm e manage-agent.
          </p>
          <div className="mt-3 flex items-center gap-3">
            <Button
              size="sm"
              onClick={() => installSkills.mutate()}
              disabled={installSkills.isPending}
            >
              {installSkills.isPending ? (
                <>
                  <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                  Installing...
                </>
              ) : (
                "Installa Skill Hermes"
              )}
            </Button>
            <span className="text-xs text-muted-foreground">
              Copia le skill in ~/.hermes/skills/
            </span>
          </div>
          {installSkills.data?.copied && (
            <div className="mt-2 text-xs text-muted-foreground">
              {installSkills.data.copied
                .filter((c) => c.name !== "AGENTS.md")
                .map((c) => (
                  <span key={c.name} className="inline-flex items-center gap-1 mr-3">
                    <span className={c.status === "installed" || c.status === "updated" ? "text-green-600" : "text-amber-600"}>
                      {c.status === "installed" ? "✅" : c.status === "updated" ? "🔄" : "⚠️"}
                    </span>
                    {c.name}
                  </span>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HermesCommandsPanel() {
  const { data: commands, isLoading } = useHermesCommands();
  const createHermesTerminal = useCreateHermesTerminal();
  const killTerminal = useKillTerminal();
  const [activeTerminalId, setActiveTerminalId] = useState<string | null>(null);
  const activeTerminalIdRef = useRef<string | null>(null);
  const [activeDialogOpen, setActiveDialogOpen] = useState(false);

  async function handleRun(cmd: { name: string; command: string }) {
    try {
      const terminal = await createHermesTerminal.mutateAsync(cmd.command);
      activeTerminalIdRef.current = terminal.id;
      setActiveTerminalId(terminal.id);
      setActiveDialogOpen(true);
    } catch {
      // toast already handled by mutation
    }
  }

  function handleDialogClose(open: boolean) {
    if (!open && activeTerminalIdRef.current) {
      killTerminal.mutate(activeTerminalIdRef.current);
      activeTerminalIdRef.current = null;
      setActiveTerminalId(null);
    }
    setActiveDialogOpen(open);
  }

  function handleSessionEnd() {
    activeTerminalIdRef.current = null;
    setActiveTerminalId(null);
    setActiveDialogOpen(false);
  }

  return (
    <>
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : !commands || commands.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nessun comando Hermes configurato. Aggiungi il setting <code>hermes_commands</code>.
        </p>
      ) : (
        <div className="space-y-3">
          {commands.map((cmd, i) => (
            <div
              key={i}
              className="border rounded-lg p-4 flex items-start gap-3"
            >
              <Terminal className="size-5 mt-0.5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{cmd.name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {cmd.description}
                </p>
                <pre className="mt-2 text-xs font-mono bg-muted rounded px-2 py-1 overflow-x-auto">
                  {cmd.command}
                </pre>
              </div>
              <Button
                size="sm"
                className="shrink-0 mt-1"
                onClick={() => handleRun(cmd)}
                disabled={createHermesTerminal.isPending}
              >
                {createHermesTerminal.isPending ? (
                  <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Play className="size-3.5 mr-1.5" />
                )}
                Run
              </Button>
            </div>
          ))}
        </div>
      )}

      <Dialog open={activeDialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="max-w-3xl h-[70vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Terminale Hermes</DialogTitle>
            <DialogDescription>
              Terminale interattivo per comandi Hermes Agent
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 min-h-0">
            {activeTerminalId && (
              <TerminalPanel
                terminalId={activeTerminalId}
                projectId=""
                onSessionEnd={handleSessionEnd}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

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

function TelegramSettingsPanel() {
  const { data: settings, isLoading } = useSettings();
  const updateSetting = useUpdateSetting();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>
    );
  }

  const botToken = settings?.find((s: Setting) => s.key === "telegram.bot_token");
  const chatId = settings?.find((s: Setting) => s.key === "telegram.chat_id");
  const notificationsEnabled = settings?.find((s: Setting) => s.key === "telegram.notifications_enabled");

  const isConfigured =
    botToken?.value &&
    chatId?.value &&
    notificationsEnabled?.value === "true";

  const [showToken, setShowToken] = useState(false);
  const [tokenInput, setTokenInput] = useState(botToken?.value ?? "");
  const [chatIdInput, setChatIdInput] = useState(chatId?.value ?? "");

  function handleToggleNotifications(enabled: boolean) {
    if (notificationsEnabled) {
      updateSetting.mutate({ key: "telegram.notifications_enabled", value: enabled ? "true" : "false" });
    }
  }

  function handleSaveToken() {
    if (botToken && tokenInput !== botToken.value) {
      updateSetting.mutate({ key: "telegram.bot_token", value: tokenInput });
    }
  }

  function handleSaveChatId() {
    if (chatId && chatIdInput !== chatId.value) {
      updateSetting.mutate({ key: "telegram.chat_id", value: chatIdInput });
    }
  }

  return (
    <div className="space-y-4">
      {/* Status indicator */}
      <div className={`border rounded-lg p-4 flex items-center gap-3 ${
        isConfigured ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
      }`}>
        <span className="text-lg">{isConfigured ? "🟢" : "🔴"}</span>
        <div>
          <p className="font-medium text-sm">
            {isConfigured ? "Telegram configurato" : "Telegram non configurato"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {isConfigured
              ? "Le notifiche Telegram sono attive e funzionanti."
              : "Inserisci il Bot Token e il Chat ID qui sotto, poi attiva le notifiche."}
          </p>
        </div>
        <span className={`ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
          isConfigured
            ? "bg-green-100 text-green-800 dark:bg-green-800/30 dark:text-green-400"
            : "bg-amber-100 text-amber-800 dark:bg-amber-800/30 dark:text-amber-400"
        }`}>
          {isConfigured ? "Attivo" : "Inattivo"}
        </span>
      </div>

      {/* Toggle notifications */}
      <div className="border rounded-lg p-4 flex items-center justify-between">
        <div className="flex items-start gap-3">
          <MessageSquare className="size-5 mt-0.5 text-primary" />
          <div>
            <p className="font-medium text-sm">Notifiche Telegram attive</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Invia notifiche su Telegram quando una issue viene completata o
              quando un agente fa una domanda.
            </p>
          </div>
        </div>
        {notificationsEnabled && (
          <button
            role="switch"
            aria-checked={notificationsEnabled.value === "true"}
            onClick={() => handleToggleNotifications(notificationsEnabled.value !== "true")}
            disabled={updateSetting.isPending}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
              notificationsEnabled.value === "true" ? "bg-primary" : "bg-input"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                notificationsEnabled.value === "true" ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        )}
      </div>

      {/* Bot Token */}
      <div className="border rounded-lg p-4">
        <label className="font-medium text-sm block mb-1">Bot Token</label>
        <p className="text-xs text-muted-foreground mb-3">
          Il token del tuo bot Telegram (da @BotFather). Verrà salvato in chiaro nel database.
        </p>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              type={showToken ? "text" : "password"}
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Inserisci il token del bot..."
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 font-mono"
            />
          </div>
          <button
            onClick={() => setShowToken(!showToken)}
            className="inline-flex items-center justify-center h-9 px-3 text-sm rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground"
            title={showToken ? "Nascondi token" : "Mostra token"}
          >
            {showToken ? "🙈" : "👁️"}
          </button>
          <button
            onClick={handleSaveToken}
            disabled={updateSetting.isPending || tokenInput === (botToken?.value ?? "")}
            className="inline-flex items-center justify-center h-9 px-4 text-sm font-medium rounded-md bg-primary text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50"
          >
            {updateSetting.isPending ? "Salvataggio..." : "Salva"}
          </button>
        </div>
      </div>

      {/* Chat ID */}
      <div className="border rounded-lg p-4">
        <label className="font-medium text-sm block mb-1">Chat ID</label>
        <p className="text-xs text-muted-foreground mb-3">
          L'ID della chat Telegram dove ricevere le notifiche (es. il tuo ID utente o un gruppo).
        </p>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={chatIdInput}
            onChange={(e) => setChatIdInput(e.target.value)}
            placeholder="Inserisci il Chat ID..."
            className="flex h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 font-mono"
          />
          <button
            onClick={handleSaveChatId}
            disabled={updateSetting.isPending || chatIdInput === (chatId?.value ?? "")}
            className="inline-flex items-center justify-center h-9 px-4 text-sm font-medium rounded-md bg-primary text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50"
          >
            {updateSetting.isPending ? "Salvataggio..." : "Salva"}
          </button>
        </div>
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
        <>
          <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-300 flex items-start gap-2">
            <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
            Server name changes take effect after restarting the backend.
          </div>
          <HermesIntegrationPanel />
        </>
      )}
      {activeTab === "Tool Descriptions" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-300 flex items-start gap-2">
          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
          Tool description changes take effect after restarting the backend.
        </div>
      )}

      {activeTab === "Terminal" ? (
        <div>
          <div className="mb-5 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300">
            These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands.
          </div>
          <TerminalCommandsEditor projectId={null} />
        </div>
      ) : activeTab === "Hermes" ? (
        <HermesCommandsPanel />
      ) : activeTab === "Preferences" ? (
        <PreferencesPanel />
      ) : activeTab === "Telegram" ? (
        <TelegramSettingsPanel />
      ) : (
        <SettingsForm settings={filteredSettings} />
      )}

      {activeTab !== "Terminal" && activeTab !== "Hermes" && activeTab !== "Preferences" && activeTab !== "Telegram" && (
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
