## ⚠️ Auto-rilevato: RuntimeError

**Errore:** No response returned.
**Fonte:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\logging_config.py:162`
**Request:** POST /mcp/

```
--- Traceback ---
Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 148, in call_next
    message = await recv_stream.receive()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\streams\memory.py", line 132, in receive
    raise EndOfStream from None
anyio.EndOfStream

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\middleware\error_logger.py", line 24, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 157, in call_next
    raise RuntimeError("No response returned.")
RuntimeError: No response returned.

--- Metadata ---
PID: 18904
Logger: app.error_service
Process: MainProcess
```