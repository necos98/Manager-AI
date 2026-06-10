## ⚠️ Auto-rilevato: NotFoundError

**Errore:** Issue not found
**Fonte:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\logging_config.py:162`
**Request:** GET /api/projects/1baae1c7-22f1-4091-abec-b49da70cf46c/issues/08097339-e8ef-49ec-82d3-84e81d538133

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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\issues.py", line 58, in get_issue
    return IssueResponse.from_record(await service.get_for_project(issue_id, project_id))
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\issue_service.py", line 133, in get_for_project
    raise NotFoundError("Issue not found")
app.exceptions.NotFoundError: Issue not found

--- Metadata ---
PID: 21064
Logger: app.error_service
Process: MainProcess
```