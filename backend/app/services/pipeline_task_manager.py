import asyncio
import logging

logger = logging.getLogger(__name__)


class PipelineTaskManager:
    def __init__(self):
        self._registry: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_task(self, run_id: str, task: asyncio.Task) -> None:
        async with self._lock:
            self._registry[run_id] = task

    async def cancel_task(self, run_id: str) -> None:
        async with self._lock:
            task = self._registry.get(run_id)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self.cleanup_task(run_id)

    async def cleanup_task(self, run_id: str) -> None:
        async with self._lock:
            self._registry.pop(run_id, None)

    def get_task(self, run_id: str) -> asyncio.Task | None:
        return self._registry.get(run_id)

    def active_runs(self) -> list[str]:
        return list(self._registry.keys())


pipeline_task_manager = PipelineTaskManager()
