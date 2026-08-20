"""内存版异步任务存储（M1 无数据库；Phase 5 落 MySQL quiz_tasks 表）

线程安全（asyncio.Lock），容量上限 + FIFO 淘汰防内存膨胀。
"""

import asyncio
from typing import Optional

MAX_TASKS = 500


class _TaskEntry:
    __slots__ = ("status", "result", "error_message")

    def __init__(self):
        self.status = "pending"
        self.result = None
        self.error_message: Optional[str] = None


class TaskStore:
    def __init__(self, max_tasks: int = MAX_TASKS):
        self._tasks: dict[str, _TaskEntry] = {}
        self._lock = asyncio.Lock()
        self._max = max_tasks

    async def create(self, task_id: str) -> None:
        async with self._lock:
            if len(self._tasks) >= self._max:
                oldest = next(iter(self._tasks))
                del self._tasks[oldest]
            self._tasks[task_id] = _TaskEntry()

    async def set_status(self, task_id: str, status: str) -> None:
        async with self._lock:
            entry = self._tasks.get(task_id)
            if entry is not None:
                entry.status = status

    async def complete(self, task_id: str, result: dict) -> None:
        async with self._lock:
            entry = self._tasks.get(task_id)
            if entry is not None:
                entry.status = "completed"
                entry.result = result

    async def fail(self, task_id: str, error_message: str) -> None:
        async with self._lock:
            entry = self._tasks.get(task_id)
            if entry is not None:
                entry.status = "failed"
                entry.error_message = error_message

    async def get(self, task_id: str) -> Optional[_TaskEntry]:
        async with self._lock:
            return self._tasks.get(task_id)


task_store = TaskStore()
