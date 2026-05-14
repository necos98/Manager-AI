"""
Ensures ProactorEventLoop is used on Windows instead of SelectorEventLoop.

uvicorn --reload triggers use_subprocess=True → asyncio_setup(True) →
WindowsSelectorEventLoopPolicy → SelectorEventLoop, which does NOT support
subprocesses on Windows (breaks MCP stdio plugins).

This module is imported at Python startup via a .pth file installed by
start.py, so it runs before uvicorn's setup_event_loop() — including in
multiprocessing worker processes spawned by uvicorn's reloader.
"""
import sys

if sys.platform == "win32":
    try:
        import uvicorn.loops.asyncio as _uv_asyncio
        _uv_asyncio.asyncio_setup = lambda use_subprocess=False: None
    except ImportError:
        pass
