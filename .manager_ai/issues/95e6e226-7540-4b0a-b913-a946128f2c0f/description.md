Bug durante eliminazione pipeline, ecco stack trace:

INFO:     127.0.0.1:54919 - "DELETE /api/projects/1baae1c7-22f1-4091-abec-b49da70cf46c/pipelines/ca428b6a-8a1b-487f-8120-33b00567bc70/steps/03ad719c-9786-4552-9704-e72e11eb4ec3 HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1936, in _exec_single_context
    self.dialect.do_executemany(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        cursor,
        ^^^^^^^
    ...<2 lines>...
        context,
        ^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\default.py", line 949, in do_executemany
    cursor.executemany(statement, parameters)
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 197, in executemany
    self._adapt_connection._handle_exception(error)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 342, in _handle_exception
    raise error
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 191, in executemany
    self.await_(_cursor.executemany(operation, seq_of_parameters))
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 47, in executemany
    await self._execute(self._cursor.executemany, sql, parameters)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 32, in _execute
    return await self._conn._execute(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 122, in _execute
    return await future
           ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 105, in run
    result = function()
sqlite3.IntegrityError: NOT NULL constraint failed: pipeline_step_runs.pipeline_step_id

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\AppData\Local\Python\pythoncore-3.14-64\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\middleware\error_logger.py", line 45, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\pipelines.py", line 128, in remove_step
    await svc.remove_step(step_id)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\pipeline_service.py", line 117, in remove_step
    await self.session.flush()
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py", line 787, in flush
    await greenlet_spawn(self.sync_session.flush, objects=objects)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 203, in greenlet_spawn
    result = context.switch(value)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 4331, in flush
    self._flush(objects)
    ~~~~~~~~~~~^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 4466, in _flush
    with util.safe_reraise():
         ~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 121, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 4427, in _flush
    flush_context.execute()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py", line 466, in execute
    rec.execute(self)
    ~~~~~~~~~~~^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py", line 642, in execute
    util.preloaded.orm_persistence.save_obj(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self.mapper,
        ^^^^^^^^^^^^
        uow.states_for_mapper_hierarchy(self.mapper, False, False),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        uow,
        ^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\persistence.py", line 85, in save_obj
    _emit_update_statements(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        base_mapper,
        ^^^^^^^^^^^^
    ...<3 lines>...
        update,
        ^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\persistence.py", line 912, in _emit_update_statements
    c = connection.execute(
        statement, multiparams, execution_options=execution_options
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1419, in execute
    return meth(
        self,
        distilled_parameters,
        execution_options or NO_OPTIONS,
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\sql\elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self, distilled_params, execution_options
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
        dialect,
    ...<8 lines>...
        cache_hit=cache_hit,
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ~~~~~~~~~~~~~~~~~~~~~~~~~^
        dialect, context, statement, parameters
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        e, str_statement, effective_parameters, cursor, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1936, in _exec_single_context
    self.dialect.do_executemany(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        cursor,
        ^^^^^^^
    ...<2 lines>...
        context,
        ^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\default.py", line 949, in do_executemany
    cursor.executemany(statement, parameters)
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 197, in executemany
    self._adapt_connection._handle_exception(error)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 342, in _handle_exception
    raise error
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 191, in executemany
    self.await_(_cursor.executemany(operation, seq_of_parameters))
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 47, in executemany
    await self._execute(self._cursor.executemany, sql, parameters)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 32, in _execute
    return await self._conn._execute(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 122, in _execute
    return await future
           ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 105, in run
    result = function()
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: pipeline_step_runs.pipeline_step_id
[SQL: UPDATE pipeline_step_runs SET pipeline_step_id=? WHERE pipeline_step_runs.id = ?]
[parameters: [(None, '150ab25b-7120-4161-94bd-ac61c23e8d63'), (None, '158cbdc0-922d-4bad-adfa-03064fbf3542'), (None, '164225c3-dc96-4b07-9326-d7df626fb120'), (None, '1cb4abae-4996-46bc-a544-517d7d25baa1'), (None, '28ae97fe-88d6-49a8-ac2f-79276193a260'), (None, '2fce4a87-e700-47f6-9170-06992a99f248'), (None, '2fed57a8-2b39-42cc-ba80-b2051dbd9259'), (None, '337665dc-1702-4b22-bbed-33b97e9cb6a0')  ... displaying 10 of 24 total bound parameter sets ...  (None, 'f06ed9a5-42a5-4d2d-ab89-065f02a29a98'), (None, 'fa56f451-c4fe-462e-b467-790418f791f2')]]
(Background on this error at: https://sqlalche.me/e/20/gkpj)