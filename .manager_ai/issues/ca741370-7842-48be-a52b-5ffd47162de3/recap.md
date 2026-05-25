## Changes

- **plugin_client.py**: 4 `logger.exception()` replaced with `logger.error()` + `logger.debug(exc_info=True)` at lines 177, 197, 250, 258. Console shows clean error only; full traceback at DEBUG level.
- **plugin_manager.py**: Removed `traceback.format_exc()` from gateway registration error log (line 118). Removed unused `import traceback`.

## Result

Plugin connection failures now show clean messages like "Plugin mysql connect failed" in console. Stack traces only visible with `LOG_LEVEL=DEBUG`. Error handling and retry logic unchanged.