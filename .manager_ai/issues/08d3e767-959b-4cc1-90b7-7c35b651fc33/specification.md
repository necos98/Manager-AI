## Bug Analysis

**Error**: `ReferenceError: useUpdateSetting is not defined` when navigating to the Settings page.

**Root Cause**: In `frontend/src/routes/settings.tsx`, the `TelegramSettingsPanel` component calls `useUpdateSetting()` on line 302, but this hook is not imported. Line 5 only imports:

```js
import { useSettings, useResetAllSettings, useInstallHermesMcp, useInstallHermesSkills, useHermesCommands } from "@/features/settings/hooks";
```

`useUpdateSetting` is exported from `@/features/settings/hooks` (line 20 of hooks.ts), so the fix is simply adding it to the existing import.

**Impact**: The entire Settings page crashes with an ErrorBoundary error whenever React tries to render the TelegramSettingsPanel component.

## Fix
Add `useUpdateSetting` to the import on line 5 of `frontend/src/routes/settings.tsx`.
