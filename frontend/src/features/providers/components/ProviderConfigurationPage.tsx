import { Bot, Loader2, ShieldCheck } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  useAgentProviderList,
  useProviderDetails,
  useDefaultProvider,
  useUpdateDefaultProvider,
} from "@/features/providers/hooks";
import type { ProviderInfo } from "@/features/providers/api";

function InstalledProviderCard({ provider }: { provider: ProviderInfo }) {
  const displayName =
    provider.name === "claude"
      ? "Claude Code"
      : provider.name === "hermes"
        ? "Hermes Agent"
        : provider.name;

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="size-5 text-primary" />
          <h3 className="font-semibold">{displayName}</h3>
          {provider.is_builtin && (
            <Badge variant="outline" className="text-xs">
              built-in
            </Badge>
          )}
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{provider.description}</p>
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">CLI:</p>
        <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
          {provider.cli} {provider.flags.join(" ")}
        </code>
      </div>
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">
          Run Issue example:
        </p>
        <code className="text-xs font-mono bg-muted px-2 py-1 rounded block whitespace-pre-wrap break-all">
          {provider.example_run_issue}
        </code>
      </div>
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">
          Run Pipeline example:
        </p>
        <code className="text-xs font-mono bg-muted px-2 py-1 rounded block whitespace-pre-wrap break-all">
          {provider.example_run_pipeline}
        </code>
      </div>
    </div>
  );
}

export function ProviderConfigurationPage() {
  const { data: providerNames, isLoading: loadingNames } =
    useAgentProviderList();
  const { data: providerDetails, isLoading: loadingDetails } =
    useProviderDetails();
  const { data: defaultProvider, isLoading: loadingDefault } =
    useDefaultProvider();
  const updateDefault = useUpdateDefaultProvider();

  const isLoading =
    loadingNames || loadingDetails || loadingDefault;

  if (isLoading) {
    return (
      <div className="p-6 flex items-center gap-2 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Loading providers...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Provider Configuration</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Choose which coding agent CLI to use for automatic operations, and
          inspect available providers.
        </p>
      </div>

      {/* Default Provider Selector */}
      <section className="border rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-5 text-primary" />
          <h2 className="font-semibold">Default Provider</h2>
          {defaultProvider && (
            <Badge variant="secondary" className="text-xs">
              Default
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          Select the default coding agent CLI for this workspace.
        </p>
        {providerNames && providerNames.length > 0 ? (
          <Select
            value={defaultProvider ?? providerNames[0]}
            onValueChange={(v) => updateDefault.mutate(v)}
          >
            <SelectTrigger className="w-64">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {providerNames.map((name) => (
                <SelectItem key={name} value={name}>
                  <span className="flex items-center gap-2">
                    {name === "claude" ? "Claude Code" : name === "hermes" ? "Hermes Agent" : name}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <p className="text-sm text-muted-foreground">
            No providers available from the API.
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          Used for: Ask &amp; Brainstorm, Manage Agent, automatic hooks, and
          fallback for agents without an explicit provider.
        </p>
      </section>

      {/* Installed Providers */}
      <section className="space-y-3">
        <h2 className="font-semibold">Installed Providers</h2>
        {providerDetails && providerDetails.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providerDetails.map((p) => (
              <InstalledProviderCard key={p.name} provider={p} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No provider details available.
          </p>
        )}
      </section>

      {/* Custom Providers (placeholder) */}
      <section className="border-2 border-dashed rounded-lg p-6 text-center space-y-2">
        <Bot className="size-8 text-muted-foreground mx-auto" />
        <h3 className="font-medium text-muted-foreground">
          Custom Providers
        </h3>
        <p className="text-sm text-muted-foreground">
          Custom providers can be added here in a future update.
        </p>
      </section>
    </div>
  );
}
