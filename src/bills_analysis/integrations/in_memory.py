from __future__ import annotations

import asyncio

from bills_analysis.models.internal import BatchRecord, QueueTask


class InMemoryBatchRepository:
    """In-memory repository implementation for local development."""

    def __init__(self) -> None:
        """Initialize thread-safe in-memory store."""

        self._items: dict[str, BatchRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, batch: BatchRecord) -> None:
        """Insert a new batch record."""

        async with self._lock:
            self._items[batch.batch_id] = batch

    async def get(self, batch_id: str) -> BatchRecord | None:
        """Get one batch by id."""

        async with self._lock:
            return self._items.get(batch_id)

    async def save(self, batch: BatchRecord) -> None:
        """Upsert batch record."""

        async with self._lock:
            self._items[batch.batch_id] = batch

    async def list(self, *, limit: int = 100) -> list[BatchRecord]:
        """Return latest batches ordered by creation time."""

        async with self._lock:
            values = sorted(self._items.values(), key=lambda x: x.created_at, reverse=True)
            return values[:limit]


class InMemoryTaskQueue:
    """In-memory queue implementation for local async worker."""

    def __init__(self) -> None:
        """Initialize queue instance."""

        self._queue: asyncio.Queue[QueueTask] = asyncio.Queue()

    async def enqueue(self, task: QueueTask) -> None:
        """Push one task into queue."""

        await self._queue.put(task)

    async def dequeue(self) -> QueueTask:
        """Pop one task from queue."""

        return await self._queue.get()

    def task_done(self) -> None:
        """Mark one dequeued task as processed."""

        self._queue.task_done()
