import { useState } from "react";
import { Plus, Trash2, ToggleLeft, ToggleRight, Globe, Terminal, Wrench } from "lucide-react";
import {
  usePlugins,
  useUpsertPlugin,
  useDeletePlugin,
  useTogglePlugin,
} from "@/features/settings/hooks-plugins";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
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

export function PluginsPanel({ projectId }: PluginsPanelProps) {
  const { data: plugins, isLoading } = usePlugins(projectId);
  const upsertPlugin = useUpsertPlugin(projectId);
  const deletePlugin = useDeletePlugin(projectId);
  const togglePlugin = useTogglePlugin(projectId);

  const [adding, setAdding] = useState(false);
  const [formKey, setFormKey] = useState("");
  const [formName, setFormName] = useState("");
  const [formTransport, setFormTransport] = useState<string>("stdio");
  const [formCommand, setFormCommand] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [formAccessLevel, setFormAccessLevel] = useState<string>("read_only");

  const resetForm = () => {
    setAdding(false);
    setFormKey("");
    setFormName("");
    setFormTransport("stdio");
    setFormCommand("");
    setFormUrl("");
    setFormAccessLevel("read_only");
  };

  const handleSave = () => {
    if (!formKey.trim()) return;
    const data: Record<string, unknown> = {
      name: formName.trim() || formKey.trim(),
      enabled: true,
      transport: formTransport,
      access_level: formAccessLevel,
      args: [],
      env: {},
      timeout: 30,
    };
    if (formTransport === "stdio") {
      data.command = formCommand.trim();
    } else {
      data.url = formUrl.trim();
    }
    upsertPlugin.mutate(
      { key: formKey.trim(), data },
      {
        onSuccess: () => {
          resetForm();
          toast.success(`Plugin "${formKey.trim()}" saved`);
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-12" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {(!plugins || plugins.length === 0) && !adding && (
        <p className="text-sm text-muted-foreground italic">
          No MCP plugins configured. Add one to extend Manager AI with external MCP tools.
        </p>
      )}

      {plugins?.map((p) => (
        <div
          key={p.key}
          className="flex items-center gap-3 p-3 border rounded-md bg-card"
        >
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
              <span className="uppercase">{p.transport}</span>
              <span>·</span>
              <span className={p.connected ? "text-green-600" : "text-red-500"}>
                {p.connected ? `${p.tool_count} tools` : "stopped"}
              </span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => togglePlugin.mutate({ key: p.key, enabled: !p.enabled })}
            aria-label={p.enabled ? "Disable" : "Enable"}
            title={p.enabled ? "Disable" : "Enable"}
          >
            {p.enabled ? (
              <ToggleRight className="size-5 text-green-600" />
            ) : (
              <ToggleLeft className="size-5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Delete plugin ${p.name}`}
            className="text-muted-foreground hover:text-destructive"
            onClick={() => {
              if (confirm(`Delete plugin "${p.name}"?`)) {
                deletePlugin.mutate(p.key);
              }
            }}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      ))}

      {adding && (
        <div className="border rounded-md p-4 space-y-3 bg-muted/30">
          <h3 className="text-sm font-semibold">New Plugin</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium">Key (unique ID)</label>
              <Input
                value={formKey}
                onChange={(e) => setFormKey(e.target.value)}
                placeholder="mysql"
                className="mt-1 font-mono text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium">Display Name</label>
              <Input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="MySQL (production)"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs font-medium">Transport</label>
              <select
                value={formTransport}
                onChange={(e) => setFormTransport(e.target.value)}
                className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
              >
                <option value="stdio">stdio (subprocess)</option>
                <option value="http">HTTP / SSE</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium">Access Level</label>
              <select
                value={formAccessLevel}
                onChange={(e) => setFormAccessLevel(e.target.value)}
                className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
              >
                <option value="read_only">read_only</option>
                <option value="read_write">read_write</option>
                <option value="admin">admin</option>
              </select>
            </div>
            {formTransport === "stdio" ? (
              <div className="col-span-2">
                <label className="text-xs font-medium">Command</label>
                <Input
                  value={formCommand}
                  onChange={(e) => setFormCommand(e.target.value)}
                  placeholder="uvx mcp-server-mysql"
                  className="mt-1 font-mono text-sm"
                />
              </div>
            ) : (
              <div className="col-span-2">
                <label className="text-xs font-medium">URL</label>
                <Input
                  value={formUrl}
                  onChange={(e) => setFormUrl(e.target.value)}
                  placeholder="https://mcp-server.internal/sse"
                  className="mt-1 font-mono text-sm"
                />
              </div>
            )}
          </div>
          <div className="flex gap-2 pt-2">
            <Button size="sm" onClick={handleSave} disabled={!formKey.trim() || upsertPlugin.isPending}>
              <Plus className="size-4 mr-1" />
              Save
            </Button>
            <Button size="sm" variant="outline" onClick={resetForm}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {!adding && (
        <div className="pt-2">
          <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
            <Plus className="size-4 mr-1" />
            Add Plugin
          </Button>
        </div>
      )}
    </div>
  );
}
