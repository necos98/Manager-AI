import { useState } from "react";
import { RotateCcw } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/shared/components/ui/tooltip";
import { useUpdateSetting, useResetSetting } from "@/features/settings/hooks";
import type { Setting } from "@/shared/types";

function formatLabel(key: string): string {
  const parts = key.split(".");
  if (parts[0] === "tool" || parts[0] === "server") {
    return parts[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return key;
}

interface SettingFieldProps {
  setting: Setting;
}

function SettingField({ setting }: SettingFieldProps) {
  const [value, setValue] = useState(setting.value);
  const updateSetting = useUpdateSetting();
  const resetSetting = useResetSetting();

  const isDirty = value !== setting.value;

  const handleSave = () => {
    updateSetting.mutate({ key: setting.key, value });
  };

  const handleReset = () => {
    resetSetting.mutate(setting.key, {
      onSuccess: () => setValue(setting.default),
    });
  };

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <label className="font-medium text-sm">{formatLabel(setting.key)}</label>
        <div className="flex items-center gap-2">
          {setting.is_customized && (
            <Badge variant="secondary" className="text-xs">Customized</Badge>
          )}
          {setting.is_customized && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={handleReset}
                    disabled={resetSetting.isPending}
                  >
                    <RotateCcw className="size-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reset to default</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={setting.key.endsWith(".description") ? 4 : 5}
        className="font-mono text-sm"
      />
      {!setting.is_customized && (
        <p className="text-xs text-muted-foreground mt-1">Default value</p>
      )}
      <div className="flex justify-end mt-2">
        <Button
          size="sm"
          onClick={handleSave}
          disabled={updateSetting.isPending || !isDirty}
        >
          {updateSetting.isPending ? "Saving..." : "Save"}
        </Button>
      </div>
    </div>
  );
}

interface SettingsFormProps {
  settings: Setting[];
}

export function SettingsForm({ settings }: SettingsFormProps) {
  if (settings.length === 0) {
    return <p className="text-sm text-muted-foreground">No settings in this category.</p>;
  }

  return (
    <div className="space-y-4">
      {settings.map((setting) => (
        <SettingField key={setting.key} setting={setting} />
      ))}
    </div>
  );
}
