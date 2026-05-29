import { useCredentialsEnv, useUpdateEnv, usePresets, useCreatePreset, useUpdatePreset, useDeletePreset, useApplyPreset } from "../hooks";
import { EnvEditor } from "./env-editor";
import { PresetsPanel } from "./presets-panel";

export function CredentialsEditorPage() {
  const { data: envData, isLoading: envLoading, isError: envError } = useCredentialsEnv();
  const { data: presets = [], isLoading: presetsLoading } = usePresets();
  const updateEnv = useUpdateEnv();
  const createPreset = useCreatePreset();
  const updatePreset = useUpdatePreset();
  const deletePreset = useDeletePreset();
  const applyPreset = useApplyPreset();

  if (envLoading || presetsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (envError) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-destructive">Failed to load credentials.</p>
      </div>
    );
  }

  return (
    <div className="p-6 h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Credentials Editor</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Edit <code className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono">
            ~/.claude/credentials.json
          </code> environment variables
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6 items-start">
        <PresetsPanel
          presets={presets}
          onCreate={(name) => {
            if (!envData) return;
            createPreset.mutate({ name, variables: envData.variables });
          }}
          onUpdate={(id, name) => updatePreset.mutate({ id, data: { name } })}
          onDelete={(id) => deletePreset.mutate(id)}
          onApply={(id) => applyPreset.mutate(id)}
          isCreating={createPreset.isPending}
          isDeleting={deletePreset.isPending}
          isApplying={applyPreset.isPending}
        />
        <EnvEditor
          key={JSON.stringify(envData?.variables ?? {})}
          variables={envData?.variables ?? {}}
          onSave={(vars) => updateEnv.mutate(vars)}
          isSaving={updateEnv.isPending}
        />
      </div>
    </div>
  );
}
