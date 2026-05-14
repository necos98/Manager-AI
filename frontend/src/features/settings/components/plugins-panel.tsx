import { useState } from "react";
import {
  Trash2, ToggleLeft, ToggleRight, Globe, Terminal, Wrench,
  Plug, Settings, Circle, Loader2,
} from "lucide-react";
import {
  usePlugins, useCatalog, useUpsertPlugin, useDeletePlugin, useTogglePlugin,
  useTestPluginConnection,
} from "@/features/settings/hooks-plugins";
import type { CatalogPlugin } from "@/features/settings/api-plugins";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/shared/components/ui/dialog";
import { Skeleton } from "@/shared/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/shared/components/ui/select";
import { toast } from "sonner";

interface PluginsPanelProps {
  projectId: string;
}

const accessLevelColors: Record<string, string> = {
  read_only: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  read_write: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  admin: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

const transportIcons: Record<string, React.ReactNode> = {
  stdio: <Terminal className="size-3.5" />,
  http: <Globe className="size-3.5" />,
};

function ConfigModal({
  open,
  onClose,
  plugin,
  projectId,
  currentConfig,
  currentEnabled,
}: {
  open: boolean;
  onClose: () => void;
  plugin: CatalogPlugin;
  projectId: string;
  currentConfig: Record<string, string>;
  currentEnabled: boolean;
}) {
  const upsertPlugin = useUpsertPlugin(projectId);
  const testConnection = useTestPluginConnection(projectId);
  const [enabled, setEnabled] = useState(currentEnabled);
  const [config, setConfig] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const opt of plugin.options) {
      initial[opt.key] = currentConfig[opt.key] ?? opt.default ?? "";
    }
    return initial;
  });

  const handleSave = () => {
    // Validate required fields
    for (const opt of plugin.options) {
      if (opt.required && !config[opt.key]?.trim()) {
        toast.error(`${opt.label} is required`);
        return;
      }
    }
    upsertPlugin.mutate(
      { key: plugin.key, enabled, config },
      {
        onSuccess: () => {
          toast.success(`${plugin.name} saved`);
          onClose();
        },
      },
    );
  };

  const handleTest = () => {
    for (const opt of plugin.options) {
      if (opt.required && !config[opt.key]?.trim()) {
        toast.error(`${opt.label} is required`);
        return;
      }
    }
    testConnection.mutate(
      { key: plugin.key, config },
      {
        onSuccess: (result) => {
          if (result.success) {
            toast.success(result.message);
          } else {
            toast.error(result.message || "Connection failed");
          }
        },
        onError: (error) => {
          const message = error instanceof Error ? error.message : "Connection test failed";
          toast.error(message);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>{plugin.name}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${accessLevelColors[plugin.access_level] ?? "bg-gray-100 text-gray-700"}`}>
              {plugin.access_level}
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">{plugin.description}</p>

          {/* Enable toggle */}
          <div className="flex items-center justify-between py-2 border-y">
            <span className="text-sm font-medium">Enable plugin</span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setEnabled(!enabled)}
              aria-label={enabled ? "Disable" : "Enable"}
            >
              {enabled ? (
                <ToggleRight className="size-5 text-green-600" />
              ) : (
                <ToggleLeft className="size-5" />
              )}
            </Button>
          </div>

          {/* Config form */}
          {plugin.options.length > 0 && enabled && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Configuration</h4>
              {plugin.options.map((opt) => (
                <div key={opt.key}>
                  <label className="text-xs font-medium">
                    {opt.label}
                    {opt.required && <span className="text-red-500 ml-0.5">*</span>}
                  </label>
                  {opt.type === "boolean" ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-1"
                      onClick={() => setConfig((c) => ({ ...c, [opt.key]: c[opt.key] === "true" ? "false" : "true" }))}
                    >
                      {config[opt.key] === "true" ? (
                        <ToggleRight className="size-4 text-green-600 mr-1" />
                      ) : (
                        <ToggleLeft className="size-4 mr-1" />
                      )}
                      {config[opt.key] === "true" ? "Yes" : "No"}
                    </Button>
                  ) : opt.type === "select" && opt.choices ? (
                    <Select
                      value={config[opt.key] || ""}
                      onValueChange={(v) => setConfig((c) => ({ ...c, [opt.key]: v }))}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder={opt.placeholder || `Select ${opt.label}`} />
                      </SelectTrigger>
                      <SelectContent>
                        {opt.choices.map((ch) => (
                          <SelectItem key={ch.value} value={ch.value}>
                            {ch.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      type={opt.type === "secret" ? "password" : opt.type === "number" ? "number" : "text"}
                      value={config[opt.key] || ""}
                      onChange={(e) => setConfig((c) => ({ ...c, [opt.key]: e.target.value }))}
                      placeholder={opt.placeholder}
                      className="mt-1"
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          {plugin.options.length === 0 && enabled && (
            <p className="text-xs text-muted-foreground italic">
              This plugin has no configurable options.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleTest}
            disabled={testConnection.isPending}
          >
            {testConnection.isPending ? (
              <><Loader2 className="size-3.5 mr-1 animate-spin" /> Testing...</>
            ) : (
              "Test Connection"
            )}
          </Button>
          <Button size="sm" onClick={handleSave} disabled={upsertPlugin.isPending}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PluginsPanel({ projectId }: PluginsPanelProps) {
  const { data: plugins, isLoading: pluginsLoading } = usePlugins(projectId);
  const { data: catalog, isLoading: catalogLoading } = useCatalog();
  const deletePlugin = useDeletePlugin(projectId);
  const togglePlugin = useTogglePlugin(projectId);

  const [configuring, setConfiguring] = useState<CatalogPlugin | null>(null);

  const isLoading = pluginsLoading || catalogLoading;

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  const pluginMap = new Map((plugins ?? []).map((p) => [p.key, p]));

  const enabledPlugins = (plugins ?? []).filter((p) => p.enabled && p.catalog);
  const legacyPlugins = (plugins ?? []).filter((p) => p.legacy);
  const availableCatalog = (catalog ?? []).filter((c) => {
    const p = pluginMap.get(c.key);
    return !p || !p.enabled;
  });

  return (
    <div className="space-y-6">
      {/* Enabled plugins */}
      {enabledPlugins.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold flex items-center gap-1.5">
            <Plug className="size-3.5" /> Enabled
          </h3>
          {enabledPlugins.map((p) => (
            <div key={p.key} className="flex items-center gap-3 p-3 border rounded-md bg-card">
              <span className="text-muted-foreground">
                {transportIcons[p.transport] ?? <Wrench className="size-3.5" />}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm truncate">{p.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${accessLevelColors[p.access_level] ?? "bg-gray-100 text-gray-700"}`}>
                    {p.access_level}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                  <span className="flex items-center gap-1">
                    <Circle className={`size-1.5 fill-current ${p.connected ? "text-green-500" : "text-red-500"}`} />
                    {p.connected ? `${p.tool_count} tools` : "stopped"}
                  </span>
                </div>
              </div>

              <Button
                variant="ghost"
                size="icon"
                title="Configure"
                onClick={() => {
                  const cat = catalog?.find((c) => c.key === p.key);
                  if (cat) setConfiguring(cat);
                }}
              >
                <Settings className="size-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => togglePlugin.mutate({ key: p.key, enabled: false })}
                aria-label="Disable"
                title="Disable"
              >
                <ToggleRight className="size-5 text-green-600" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Available catalog */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Available Plugins</h3>
        {availableCatalog.length === 0 && enabledPlugins.length === 0 && (
          <p className="text-sm text-muted-foreground italic">
            No plugins available. Add plugin manifests to <code className="text-xs bg-muted px-1 rounded">backend/plugins/</code>.
          </p>
        )}
        {availableCatalog.length === 0 && enabledPlugins.length > 0 && (
          <p className="text-sm text-muted-foreground italic">
            All available plugins are enabled.
          </p>
        )}
        <div className="grid gap-2 sm:grid-cols-2">
          {availableCatalog.map((cat) => (
            <div key={cat.key} className="flex items-start gap-3 p-3 border rounded-md bg-card">
              <span className="text-muted-foreground mt-0.5">
                {transportIcons[cat.transport] ?? <Wrench className="size-3.5" />}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm truncate">{cat.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${accessLevelColors[cat.access_level] ?? "bg-gray-100 text-gray-700"}`}>
                    {cat.access_level}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                  {cat.description}
                </p>
                {cat.options.length > 0 && (
                  <p className="text-[10px] text-muted-foreground mt-1">
                    {cat.options.length} option{cat.options.length !== 1 ? "s" : ""}
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                onClick={() => setConfiguring(cat)}
              >
                Configure
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Legacy plugins */}
      {legacyPlugins.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold flex items-center gap-1.5 text-muted-foreground">
            <Wrench className="size-3.5" /> Legacy Plugins
          </h3>
          <p className="text-xs text-muted-foreground">
            These plugins were created before the catalog system. They cannot be edited — only disabled or deleted.
          </p>
          {legacyPlugins.map((p) => (
            <div key={p.key} className="flex items-center gap-3 p-3 border rounded-md bg-muted/30">
              <Wrench className="size-3.5 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <span className="font-medium text-sm truncate">{p.name}</span>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                  <span className={p.connected ? "text-green-600" : "text-red-500"}>
                    {p.connected ? `${p.tool_count} tools` : "stopped"}
                  </span>
                </div>
              </div>
              {p.enabled && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => togglePlugin.mutate({ key: p.key, enabled: false })}
                  aria-label="Disable"
                  title="Disable"
                >
                  <ToggleRight className="size-5 text-green-600" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Delete legacy plugin ${p.name}`}
                className="text-muted-foreground hover:text-destructive"
                onClick={() => {
                  if (confirm(`Delete legacy plugin "${p.name}"?`)) {
                    deletePlugin.mutate(p.key);
                  }
                }}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Config modal */}
      {configuring && (
        <ConfigModal
          open={!!configuring}
          onClose={() => setConfiguring(null)}
          plugin={configuring}
          projectId={projectId}
          currentConfig={pluginMap.get(configuring.key)?.config ?? {}}
          currentEnabled={pluginMap.get(configuring.key)?.enabled ?? false}
        />
      )}
    </div>
  );
}
