1|import { useState } from "react";
2|import { createFileRoute } from "@tanstack/react-router";
3|import { AlertTriangle, Loader2, Bot } from "lucide-react";
4|import { useSettings, useResetAllSettings, useInstallHermesMcp } from "@/features/settings/hooks";
5|import { SettingsForm } from "@/features/settings/components/settings-form";
6|import { TerminalCommandsEditor } from "@/features/terminals/components/terminal-commands-editor";
7|import { Button } from "@/shared/components/ui/button";
8|import {
9|  Dialog,
10|  DialogContent,
11|  DialogDescription,
12|  DialogFooter,
13|  DialogHeader,
14|  DialogTitle,
15|} from "@/shared/components/ui/dialog";
16|import { Skeleton } from "@/shared/components/ui/skeleton";
17|import type { Setting } from "@/shared/types";
18|
19|const TABS = ["Server", "Tool Descriptions", "Response Messages", "Terminal", "Claude", "Preferences"] as const;
20|type SettingsTab = (typeof TABS)[number];
21|
22|function getCategory(key: string): string {
23|  if (key.startsWith("server.")) return "Server";
24|  if (key.endsWith(".description")) return "Tool Descriptions";
25|  if (key.endsWith(".response_message")) return "Response Messages";
26|  if (key.startsWith("claude.") || key === "ask_brainstorm_command") return "Claude";
27|  return "Other";
28|}
29|
30|export const Route = createFileRoute("/settings")({
31|  component: SettingsPage,
32|});
33|
34|
function HermesIntegrationPanel() {
  const install = useInstallHermesMcp();

  return (
    <div className="border rounded-lg p-4 mt-5">
      <div className="flex items-start gap-3">
        <Bot className="size-5 mt-0.5 text-primary" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">Hermes Agent Integration</p>
          <p className="text-xs text-muted-foreground mt-1">
            Connect Hermes Agent to the Manager AI MCP server. This allows
            Hermes to directly manage issues, pipelines, memories, and more
            through the Manager AI backend.
          </p>
          <div className="mt-3 flex items-center gap-3">
            <Button
              size="sm"
              onClick={() => install.mutate()}
              disabled={install.isPending}
            >
              {install.isPending ? (
                <>
                  <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                  Installing...
                </>
              ) : (
                "Installa MCP su Hermes"
              )}
            </Button>
            <span className="text-xs text-muted-foreground">
              Esegue: hermes mcp add manager-ai --url http://localhost:8000/mcp
            </span>
          </div>
          {install.data && !install.data.success && install.data.error && (
            <p className="mt-2 text-xs text-destructive">{install.data.error}</p>
          )}
          {install.data?.stdout && (
            <pre className="mt-2 text-xs bg-muted p-2 rounded max-h-24 overflow-auto">
              {install.data.stdout}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

function PreferencesPanel() {
35|  const [soundEnabled, setSoundEnabled] = useState(
36|    () => localStorage.getItem("manager_ai_sound") !== "false"
37|  );
38|
39|  function handleToggleSound(enabled: boolean) {
40|    setSoundEnabled(enabled);
41|    localStorage.setItem("manager_ai_sound", enabled ? "true" : "false");
42|  }
43|
44|  return (
45|    <div className="space-y-4">
46|      <div className="border rounded-lg p-4 flex items-center justify-between">
47|        <div>
48|          <p className="font-medium text-sm">Sound Notifications</p>
49|          <p className="text-xs text-muted-foreground mt-0.5">
50|            Play a sound when events arrive
51|          </p>
52|        </div>
53|        <button
54|          role="switch"
55|          aria-checked={soundEnabled}
56|          onClick={() => handleToggleSound(!soundEnabled)}
57|          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
58|            soundEnabled ? "bg-primary" : "bg-input"
59|          }`}
60|        >
61|          <span
62|            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
63|              soundEnabled ? "translate-x-6" : "translate-x-1"
64|            }`}
65|          />
66|        </button>
67|      </div>
68|    </div>
69|  );
70|}
71|
72|function SettingsPage() {
73|  const { data: settings, isLoading, error } = useSettings();
74|  const resetAll = useResetAllSettings();
75|  const [activeTab, setActiveTab] = useState<SettingsTab>("Server");
76|  const [showResetConfirm, setShowResetConfirm] = useState(false);
77|
78|  if (isLoading) {
79|    return (
80|      <div className="p-6 space-y-4">
81|        <Skeleton className="h-8 w-32" />
82|        <Skeleton className="h-10 w-96" />
83|        {[1, 2, 3].map((i) => (
84|          <Skeleton key={i} className="h-40" />
85|        ))}
86|      </div>
87|    );
88|  }
89|
90|  if (error) {
91|    return (
92|      <div className="p-6">
93|        <p className="text-destructive">{error.message}</p>
94|      </div>
95|    );
96|  }
97|
98|  const filteredSettings = (settings ?? []).filter(
99|    (s: Setting) => getCategory(s.key) === activeTab,
100|  );
101|
102|  return (
103|    <div className="p-6">
104|      <h1 className="text-xl font-semibold mb-6">Settings</h1>
105|
106|      <div className="flex gap-1.5 mb-6">
107|        {TABS.map((tab) => (
108|          <Button
109|            key={tab}
110|            variant={activeTab === tab ? "default" : "outline"}
111|            size="sm"
112|            onClick={() => setActiveTab(tab)}
113|            className="text-xs"
114|          >
115|            {tab}
116|          </Button>
117|        ))}
118|      </div>
119|
120|      {activeTab === "Server" && (
121|        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-300 flex items-start gap-2">
122|          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
123|          Server name changes take effect after restarting the backend.
124|        </div>
125|      )}
126|      {activeTab === "Tool Descriptions" && (
127|        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-300 flex items-start gap-2">
128|          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
129|          Tool description changes take effect after restarting the backend.
130|        </div>
131|      )}
132|
133|      {activeTab === "Terminal" ? (
134|        <div>
135|          <div className="mb-5 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300">
136|            These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands.
137|          </div>
138|          <TerminalCommandsEditor projectId={null} />
139|        </div>
140|      ) : activeTab === "Preferences" ? (
141|        <PreferencesPanel />
142|      ) : (
143|        <SettingsForm settings={filteredSettings} />
144|      )}
145|
146|      {activeTab !== "Terminal" && activeTab !== "Preferences" && (
147|        <div className="mt-8 pt-6 border-t">
148|          <Button
149|            variant="ghost"
150|            size="sm"
151|            className="text-destructive hover:text-destructive"
152|            onClick={() => setShowResetConfirm(true)}
153|          >
154|            Reset all to defaults
155|          </Button>
156|        </div>
157|      )}
158|
159|      <Dialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
160|        <DialogContent>
161|          <DialogHeader>
162|            <DialogTitle>Reset All Settings?</DialogTitle>
163|            <DialogDescription>
164|              This will reset all settings to their default values. This action cannot be undone.
165|            </DialogDescription>
166|          </DialogHeader>
167|          <DialogFooter>
168|            <Button variant="outline" onClick={() => setShowResetConfirm(false)}>
169|              Cancel
170|            </Button>
171|            <Button
172|              variant="destructive"
173|              onClick={() => resetAll.mutate(undefined, { onSuccess: () => setShowResetConfirm(false) })}
174|              disabled={resetAll.isPending}
175|            >
176|              {resetAll.isPending ? "Resetting..." : "Confirm"}
177|            </Button>
178|          </DialogFooter>
179|        </DialogContent>
180|      </Dialog>
181|    </div>
182|  );
183|}
184|