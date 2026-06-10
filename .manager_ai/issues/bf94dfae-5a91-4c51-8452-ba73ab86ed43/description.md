## ⚠️ Auto-rilevato: NotFoundError

**Errore:** Project not found
**Fonte:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\logging_config.py:162`
**Request:** GET /api/projects/files

```
--- Traceback ---
Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 301, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 212, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\projects.py", line 310, in get_project
    project = await service.get_by_id(project_id)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\project_service.py", line 66, in get_by_id
    raise NotFoundError("Project not found")
app.exceptions.NotFoundError: Project not found

--- Metadata ---
PID: 21956
Logger: app.error_service
Process: MainProcess
```