HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 177, in _call_
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~^^
  |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\anyio\backends\_asyncio.py", line 799, in __aexit_
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    |     result = await app(  # type: ignore[func-returns-value]
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |         self.scope, self.receive, self.send
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in _call_
    |     return await self.app(scope, receive, send)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\fastapi\applications.py", line 1054, in _call_
    |     await super()._call_(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\applications.py", line 112, in _call_
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 187, in _call_
    |     raise exc
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 165, in _call_
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 85, in _call_
    |     await self.app(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 176, in _call_
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~^^
    |   File "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3568.0_x64_qbz5n2kfra8p0\Lib\contextlib.py", line 162, in __exit_
    |     self.gen.throw(value)
    |     ~~~~~~^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 178, in _call_
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\backend\app\middleware\error_logger.py", line 45, in dispatch
    |     return await call_next(request)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in _call_
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 714, in _call_
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 301, in app
    |     raw_response = await run_endpoint_function(
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     ...<3 lines>...
    |     )
    |     ^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 212, in run_endpoint_function
    |     return await dependant.call(**values)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\backend\app\routers\issue_relations.py", line 23, in get_relations
    |     views = await svc.get_relations_for_issue(issue_id)
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\backend\app\services\issue_relation_service.py", line 86, in get_relations_for_issue
    |     for rel in issue.relations:
    |                ^^^^^^^^^^^^^^^
    | AttributeError: 'NoneType' object has no attribute 'relations'
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in _call_
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\fastapi\applications.py", line 1054, in _call_
    await super()._call_(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\applications.py", line 112, in _call_
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 187, in _call_
    raise exc
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 165, in _call_
    await self.app(scope, receive, _send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 85, in _call_
    await self.app(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 176, in _call_
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~^^
  File "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3568.0_x64_qbz5n2kfra8p0\Lib\contextlib.py", line 162, in __exit_
    self.gen.throw(value)
    ~~~~~~^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 178, in _call_
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\backend\app\middleware\error_logger.py", line 45, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in _call_
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 714, in _call_
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 301, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 212, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\backend\app\routers\issue_relations.py", line 23, in get_relations
    views = await svc.get_relations_for_issue(issue_id)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\g.moroni\Desktop\comevuoi\Manager-AI\backend\app\services\issue_relation_service.py", line 86, in get_relations_for_issue
    for rel in issue.relations:
               ^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'relations'