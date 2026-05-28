Bug quando apro la pagina degli agenti:

INFO:     127.0.0.1:62524 - "GET /api/agents HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 799, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    |     result = await app(  # type: ignore[func-returns-value]
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |         self.scope, self.receive, self.send
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    |     return await self.app(scope, receive, send)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Users\j.magarelli\AppData\Local\Python\pythoncore-3.14-64\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\middleware\error_logger.py", line 45, in dispatch
    |     return await call_next(request)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 301, in app
    |     raw_response = await run_endpoint_function(
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     ...<3 lines>...
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 212, in run_endpoint_function
    |     return await dependant.call(**values)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\agents.py", line 27, in list_agents
    |     return [_response(a) for a in agents]
    |             ~~~~~~~~~^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\agents.py", line 12, in _response
    |     return AgentResponse(
    |         id=agent.id,
    |     ...<5 lines>...
    |         updated_at=str(agent.updated_at) if agent.updated_at else None,
    |     )
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\pydantic\main.py", line 250, in __init__
    |     validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
    | pydantic_core._pydantic_core.ValidationError: 1 validation error for AgentResponse
    | project_id
    |   Field required [type=missing, input_value={'id': 'f273f92c-5afb-47a...: '2026-05-28 19:54:57'}, input_type=dict]
    |     For further information visit https://errors.pydantic.dev/2.12/v/missing
    +------------------------------------