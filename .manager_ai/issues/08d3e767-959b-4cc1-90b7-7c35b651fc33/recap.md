## Recap

**Bug**: `ReferenceError: useUpdateSetting is not defined` on the Settings page.

**Root cause**: In `frontend/src/routes/settings.tsx`, the `TelegramSettingsPanel` component uses `useUpdateSetting()` but the hook was not imported. The import on line 5 was missing `useUpdateSetting` from `@/features/settings/hooks`.

**Fix**: Added `useUpdateSetting` to the existing import statement. TypeScript check passes cleanly.

**File changed**: `frontend/src/routes/settings.tsx` — 1 line changed.