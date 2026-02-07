from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from bills_analysis.models.enums import BatchStatus, TaskType
from bills_analysis.services.ports import BatchRepository, ProcessingBackend, TaskQueue


class BatchWorker:
    """Queue worker that executes process/merge tasks."""

    def __init__(
        self,
        *,
        repo: BatchRepository,
        queue: TaskQueue,
        backend: ProcessingBackend,
    ) -> None:
        """Bind repository, queue and backend adapters."""

        self.repo = repo
        self.queue = queue
        self.backend = backend

    async def run_forever(self) -> None:
        """Continuously consume queue tasks."""

        while True:
            await self.run_once()

    async def run_once(self) -> None:
        """Process a single queue task and update batch state."""

        task = await self.queue.dequeue()
        try:
            batch = await self.repo.get(task.batch_id)
            if batch is None:
                return
            if task.task_type == TaskType.PROCESS_BATCH:
                batch.status = BatchStatus.RUNNING
                batch.updated_at = datetime.now(UTC)
                await self.repo.save(batch)
                artifacts = await self.backend.process_batch(batch)
                batch.artifacts.update(artifacts)
                batch.status = BatchStatus.REVIEW_READY
                batch.error = None
                batch.updated_at = datetime.now(UTC)
                await self.repo.save(batch)
                return
            if task.task_type == TaskType.MERGE_BATCH:
                output = await self.backend.merge_batch(batch, task.payload)
                batch.merge_output = output
                batch.status = BatchStatus.MERGED
                batch.error = None
                batch.updated_at = datetime.now(UTC)
                await self.repo.save(batch)
                return
        except Exception as exc:  # pragma: no cover - defensive runtime safety
            batch = await self.repo.get(task.batch_id)
            if batch is not None:
                batch.status = BatchStatus.FAILED
                batch.error = str(exc)
                batch.updated_at = datetime.now(UTC)
                await self.repo.save(batch)
        finally:
            self.queue.task_done()


async def run_worker(worker: BatchWorker) -> None:
    """Async entrypoint for external runner integration."""

    await worker.run_forever()


def run_worker_sync(worker: BatchWorker) -> None:
    """Sync entrypoint for local scripts/CLI."""

    asyncio.run(run_worker(worker))
