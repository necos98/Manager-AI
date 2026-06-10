## ⚠️ Auto-rilevato: ExceptionGroup

**Errore:** unhandled errors in a TaskGroup (1 sub-exception)
**Fonte:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\mcp\server\streamable_http.py:520`
**Request:**  N/A

```
--- Traceback ---
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\mcp\server\streamable_http.py", line 513, in _handle_post_request
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 799, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\mcp\server\streamable_http.py", line 518, in _handle_post_request
    |     await writer.send(session_message)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\streams\memory.py", line 249, in send
    |     self.send_nowait(item)
    |     ~~~~~~~~~~~~~~~~^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\streams\memory.py", line 218, in send_nowait
    |     raise ClosedResourceError
    | anyio.ClosedResourceError
    +------------------------------------

--- Metadata ---
PID: 18904
Logger: mcp.server.streamable_http
Process: MainProcess
```