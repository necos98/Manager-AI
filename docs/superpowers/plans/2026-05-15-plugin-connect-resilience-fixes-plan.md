# Plugin Connect Resilience Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five issues found in self-review of the initial `ClosedResourceError` fix: cancelled task propagation, wasted wait on pre-connect failure, race window between `_connected` and `_connect_ready`, configurable `connect_timeout`, and missing coordination tests.

**Architecture:** Incremental hardening of `PluginClient` and `PluginManager`. Adds `_connect_done` event for failure-awareness, moves `_connect_ready.set()` into `_init_session()` for atomicity, makes `connect_timeout` a catalog-level config field, and adds four tests for the pre-connect coordination flow.

**Tech Stack:** Python 3.14, asyncio, pytest + pytest-asyncio, FastMCP

---

### Task 1: Add `connect_timeout` to CatalogPlugin and PluginConfig

**Files:**
- Modify: `backend/app/mcp/catalog.py`
- Modify: `backend/app/mcp/plugin_config.py`
- Modify: `backend/app/mcp/plugin_manager.py` (2 lines in `_start_one` and `restart_plugin`)

- [ ] **Step 1: Add `connect_timeout` to `CatalogPlugin`**

In `backend/app/mcp/catalog.py`, add field to `CatalogPlugin`:

```python
class CatalogPlugin(BaseModel):
    key: str
    name: str
    description: str = ""
    transport: PluginTransport = PluginTransport.stdio
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    access_level: AccessLevel = AccessLevel.read_only
    timeout: int = 30
    connect_timeout: int = 20  # <-- add this line
    options: list[OptionDef] = Field(default_factory=list)
```

- [ ] **Step 2: Add `connect_timeout` to `build_runtime_config()` output**

In `backend/app/mcp/catalog.py`, in `build_runtime_config()`:

```python
def build_runtime_config(
    self, catalog_key: str, enabled: bool, user_config: dict[str, str]
) -> "PluginConfig | None":
    from app.mcp.plugin_config import PluginConfig

    cat = self.get(catalog_key)
    if cat is None:
        return None
    return PluginConfig(
        name=cat.name,
        enabled=enabled,
        transport=cat.transport,
        command=cat.command,
        args=cat.args,
        url=cat.url,
        env=user_config,
        access_level=cat.access_level,
        timeout=cat.timeout,
        connect_timeout=cat.connect_timeout,  # <-- add this line
    )
```

- [ ] **Step 3: Add `connect_timeout` to `PluginConfig`**

In `backend/app/mcp/plugin_config.py`, add field to `PluginConfig`:

```python
class PluginConfig(BaseModel):
    name: str = ""
    enabled: bool = True
    transport: PluginTransport = PluginTransport.stdio
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    env: dict[str, str] = Field(default_factory=dict)
    access_level: AccessLevel = AccessLevel.read_only
    timeout: int = 30
    connect_timeout: int = 20  # <-- add this line
```

- [ ] **Step 4: Use `cfg.connect_timeout` in `_start_one` and `restart_plugin`**

In `backend/app/mcp/plugin_manager.py`, replace hand-rolled computation in both places.

`_start_one` (line ~96):
```python
# Before:
connect_timeout = min(cfg.timeout, 20) if cfg.timeout else 20

# After:
connect_timeout = cfg.connect_timeout
```

Same change in `restart_plugin` (line ~205).

- [ ] **Step 5: Run existing tests to confirm no regression**

```powershell
cd backend; python -m pytest tests/test_plugin_manager.py tests/test_plugin_descriptions.py -v
```
Expected: 28 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/catalog.py backend/app/mcp/plugin_config.py backend/app/mcp/plugin_manager.py
git commit -m "feat: make plugin connect_timeout configurable via catalog

Adds connect_timeout field (default 20s) to CatalogPlugin, PluginConfig,
and build_runtime_config(). plugin_manager.py uses it directly instead
of hardcoding min(cfg.timeout, 20)."
```

---

### Task 2: Fix `BaseException` → `Exception` in pre-connect closures

**Files:**
- Modify: `backend/app/mcp/plugin_manager.py` (two closures)

- [ ] **Step 1: Change `except BaseException` to `except Exception` in `_start_one`**

In `backend/app/mcp/plugin_manager.py`, `_start_one` method, `_pre_connect` closure:

```python
# Before:
            except BaseException:
                logger.debug("Plugin %s background pre-connect failed (will retry on first call)", key)

# After:
            except Exception:
                logger.debug("Plugin %s background pre-connect failed (will retry on first call)", key)
```

- [ ] **Step 2: Same change in `restart_plugin`**

In `backend/app/mcp/plugin_manager.py`, `restart_plugin` method, `_pre_connect` closure:

```python
# Before:
                except BaseException:
                    logger.debug("Plugin %s background pre-connect failed (will retry on first call)", plugin_key)

# After:
                except Exception:
                    logger.debug("Plugin %s background pre-connect failed (will retry on first call)", plugin_key)
```

- [ ] **Step 3: Run tests**

```powershell
cd backend; python -m pytest tests/test_plugin_manager.py -v
```
Expected: 23 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/mcp/plugin_manager.py
git commit -m "fix: use except Exception not BaseException in pre-connect tasks

BaseException catches asyncio.CancelledError, preventing task cancellation.
Exception is sufficient for connect() failures and lets CancelledError
propagate so the task shows as cancelled() instead of done()."
```

---

### Task 3: Move `_connect_ready.set()` into `_init_session()`

**Files:**
- Modify: `backend/app/mcp/plugin_client.py`

- [ ] **Step 1: Add `_connect_ready.set()` in `_init_session` after `_connected = True`**

In `backend/app/mcp/plugin_client.py`, `_init_session` method:

```python
async def _init_session(self, read_stream: Any, write_stream: Any) -> None:
    self._session = ClientSession(read_stream, write_stream)
    await self._session.__aenter__()
    await self._session.initialize()
    result = await self._session.list_tools()
    self._tools = list(result.tools) if result.tools else []
    self._connected = True
    self._connect_ready.set()  # <-- add here, right after _connected = True
    logger.info(
        "Plugin %s connected with %d tools: %s",
        self.plugin_name,
        len(self._tools),
        [t.name for t in self._tools],
    )
```

- [ ] **Step 2: Remove `_connect_ready.set()` from `connect()`**

In `backend/app/mcp/plugin_client.py`, `connect` method, remove the `self._connect_ready.set()` line:

```python
# Before:
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")
            self._connect_ready.set()
        except BaseException:

# After:
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")
        except BaseException:
```

- [ ] **Step 3: Run tests**

```powershell
cd backend; python -m pytest tests/test_plugin_manager.py tests/test_plugin_descriptions.py -v
```
Expected: 28 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/mcp/plugin_client.py
git commit -m "fix: close race window between _connected and _connect_ready

Move _connect_ready.set() into _init_session() right after _connected=True
so no observer can see _connected=True with the event unset. Removes the
gap where disconnect() could interleave and leave the event in a stale state."
```

---

### Task 4: Add `_connect_done` event for failure-aware wakeup

**Files:**
- Modify: `backend/app/mcp/plugin_client.py`

- [ ] **Step 1: Add `_connect_done` field**

In `backend/app/mcp/plugin_client.py`, `PluginClient` dataclass, after `_connect_ready`:

```python
    _connect_ready: asyncio.Event = field(default_factory=asyncio.Event, repr=False, init=False)
    _connect_done: asyncio.Event = field(default_factory=asyncio.Event, repr=False, init=False)
```

- [ ] **Step 2: Set `_connect_done` in `finally` block inside `connect()`**

In `backend/app/mcp/plugin_client.py`, `connect` method:

```python
    async def connect(self) -> None:
        if self._connected:
            return
        try:
            if self.transport == "stdio":
                await self._connect_stdio()
            elif self.transport == "http":
                await self._connect_http()
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")
        except BaseException:
            logger.exception("Plugin %s connect failed", self.plugin_name)
            await self._cleanup_on_connect_failure()
            raise
        finally:
            self._connect_done.set()
```

- [ ] **Step 3: Clear `_connect_done` in `_cleanup_on_connect_failure()`**

```python
    async def _cleanup_on_connect_failure(self) -> None:
        """Clean up state after a failed connect() attempt."""
        self._connected = False
        self._connect_ready.clear()
        self._connect_done.clear()  # <-- add
        await self._exit_transport()
        self._cleanup_stderr_file()
```

- [ ] **Step 4: Clear `_connect_done` in `disconnect()`**

```python
    async def disconnect(self) -> None:
        self._connected = False
        self._connect_ready.clear()
        self._connect_done.clear()  # <-- add
        await self._exit_transport()
        self._cleanup_stderr_file()
        self._tools.clear()
```

- [ ] **Step 5: Rewrite `ensure_connected()` to wait on `_connect_done` instead of `_connect_ready`**

```python
    async def ensure_connected(self) -> None:
        """Connect if not already connected.

        Waits for a background pre-connect task (if one exists) up to
        *connect_timeout* seconds.  If the pre-connect hasn't finished by
        then, or if there is no pre-connect task, we start our own
        time-bounded connect.

        The deadline is deliberately shorter than the MCP client's SSE
        timeout (~60 s) so we can return a friendly error instead of
        crashing with ClosedResourceError when the client disconnects first.
        """
        if self._connected:
            return

        # Wait for _connect_done — set in connect()'s finally block, so it
        # fires on both success and failure.  This avoids wasting the full
        # connect_timeout when the pre-connect fails quickly.
        try:
            await asyncio.wait_for(
                self._connect_done.wait(),
                timeout=self.connect_timeout,
            )
        except asyncio.TimeoutError:
            pass

        if self._connected:
            return

        # Only start our own connect when no pre-connect task is still
        # running.  If one is in flight we let it finish on its own — the
        # next call will pick up the result.
        pre_connect_running = (
            self._pre_connect_task is not None
            and not self._pre_connect_task.done()
        )

        if not pre_connect_running:
            async with self._connect_lock:
                if self._connected:
                    return
                try:
                    await asyncio.wait_for(
                        self.connect(),
                        timeout=self.connect_timeout,
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError(
                        f"Plugin {self.plugin_name} connection timed out "
                        f"after {self.connect_timeout}s"
                    )
        else:
            raise RuntimeError(
                f"Plugin {self.plugin_name} still initializing — "
                "pre-connect in progress, retry shortly"
            )
```

Key change from previous version: `_connect_done.wait()` instead of `_connect_ready.wait()`. When the pre-connect fails in 2s, the `finally` block sets `_connect_done`, the waiter wakes immediately, sees `_connected=False`, and starts its own connect without wasting 18s.

- [ ] **Step 6: Run tests**

```powershell
cd backend; python -m pytest tests/test_plugin_manager.py tests/test_plugin_descriptions.py -v
```
Expected: 28 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/mcp/plugin_client.py
git commit -m "feat: add _connect_done event for failure-aware wakeup

ensure_connected() now waits on _connect_done (set in connect()'s finally)
instead of _connect_ready (set only on success). When pre-connect fails
quickly, waiters wake immediately rather than blocking for the full
connect_timeout."
```

---

### Task 5: Add tests for pre-connect coordination

**Files:**
- Modify: `backend/tests/test_plugin_manager.py`

- [ ] **Step 1: Add `import contextlib` at top of test file**

In `backend/tests/test_plugin_manager.py`, add to imports:

```python
import contextlib
```

- [ ] **Step 2: Add `TestEnsureConnectedCoordination` class with first test — already connected returns immediately**

```python
class TestEnsureConnectedCoordination:
    @pytest.mark.asyncio
    async def test_returns_immediately_when_already_connected(self):
        """_connected=True -> ensure_connected() returns without waiting."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=5,
        )
        client._connected = True
        client._connect_ready.set()
        client._connect_done.set()

        # Should return immediately — no exception, no delay
        await asyncio.wait_for(client.ensure_connected(), timeout=1.0)
```

- [ ] **Step 3: Test — pre-connect still running raises RuntimeError**

```python
    @pytest.mark.asyncio
    async def test_raises_when_pre_connect_still_running(self):
        """Pre-connect task not done -> RuntimeError, no crash."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=1,  # short so test is fast
        )
        # Simulate pre-connect task that never finishes
        async def never_finish():
            await asyncio.Event().wait()
        client._pre_connect_task = asyncio.create_task(never_finish())

        with pytest.raises(RuntimeError, match="still initializing"):
            await client.ensure_connected()

        # Cleanup: cancel the never-finishing task
        client._pre_connect_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await client._pre_connect_task
```

- [ ] **Step 4: Test — pre-connect failed, falls back to own connect**

```python
    @pytest.mark.asyncio
    async def test_own_connect_when_pre_connect_failed(self):
        """Pre-connect task done (failed) -> tries own connect()."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=0.5,
        )
        # Simulate failed pre-connect: task done with exception
        async def fail():
            raise RuntimeError("boom")
        task = asyncio.create_task(fail())
        with contextlib.suppress(RuntimeError):
            await task
        client._pre_connect_task = task

        # Mock connect to verify it's called (instead of relying on
        # real connect which depends on OS-specific subprocess behavior).
        connect_called = False

        async def mock_connect():
            nonlocal connect_called
            connect_called = True
            client._connected = True
            client._connect_ready.set()

        client.connect = mock_connect  # type: ignore[method-assign]

        await client.ensure_connected()
        assert connect_called, "own connect() should have been called after pre-connect failure"
        assert client._connected is True
```

- [ ] **Step 5: Test — connect timeout raises RuntimeError**

```python
    @pytest.mark.asyncio
    async def test_connect_timeout_raises_runtime_error(self):
        """connect() takes > connect_timeout -> RuntimeError."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=0.2,
        )
        # Mock connect to hang forever.  Assigning a plain function to
        # client.connect means self.connect() calls it without implicit
        # self — no binding issues.
        async def slow_connect():
            await asyncio.Event().wait()

        client.connect = slow_connect  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="connection timed out"):
            await client.ensure_connected()
```

- [ ] **Step 6: Run the new tests**

```powershell
cd backend; python -m pytest tests/test_plugin_manager.py::TestEnsureConnectedCoordination -v
```
Expected: 4 passed.

- [ ] **Step 7: Run all plugin tests**

```powershell
cd backend; python -m pytest tests/test_plugin_manager.py tests/test_plugin_descriptions.py -v
```
Expected: 32 passed (28 + 4 new).

- [ ] **Step 8: Commit**

```bash
git add backend/tests/test_plugin_manager.py
git commit -m "test: add pre-connect coordination tests for ensure_connected

Covers: already-connected fast path, pre-connect-in-progress error,
pre-connect-failed fallback, and connect-timeout error."
```
