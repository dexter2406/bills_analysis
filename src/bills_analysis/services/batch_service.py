from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bills_analysis.models.api_requests import CreateBatchRequest, MergeRequest, SubmitReviewRequest
from bills_analysis.models.enums import BatchStatus, TaskType
from bills_analysis.models.internal import BatchRecord, QueueTask
from bills_analysis.services.ports import BatchRepository, TaskQueue


class BatchService:
    """Application service orchestrating batch lifecycle transitions."""

    def __init__(self, repo: BatchRepository, queue: TaskQueue) -> None:
        """Bind repository and queue implementations."""

        self.repo = repo
        self.queue = queue

    async def create_batch(self, req: CreateBatchRequest) -> BatchRecord:
        """Persist a new batch and enqueue processing task."""

        batch, _ = await self.create_batch_with_task(req)
        return batch

    async def create_batch_with_task(self, req: CreateBatchRequest) -> tuple[BatchRecord, QueueTask]:
        """Persist a batch and return the corresponding queued process task."""

        batch = BatchRecord.new(req)
        task = QueueTask.new(batch_id=batch.batch_id, task_type=TaskType.PROCESS_BATCH)
        await self.repo.create(batch)
        await self.queue.enqueue(task)
        return batch, task

    async def get_batch(self, batch_id: str) -> BatchRecord | None:
        """Load a batch by id."""

        return await self.repo.get(batch_id)

    async def list_batches(self, *, limit: int = 100) -> list[BatchRecord]:
        """List latest batches for API query."""

        return await self.repo.list(limit=limit)

    async def save_review(self, batch_id: str, review: SubmitReviewRequest) -> BatchRecord:
        """Save reviewed rows to an existing batch."""

        batch = await self.repo.get(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        batch.review_rows = review.rows
        batch.updated_at = datetime.now(UTC)
        await self.repo.save(batch)
        return batch

    async def get_review_rows(self, batch_id: str) -> tuple[BatchRecord, list[dict[str, Any]]]:
        """Fetch current review rows for one batch."""

        batch = await self.repo.get(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        return batch, list(batch.review_rows)

    async def save_merge_source_local(self, batch_id: str, monthly_excel_path: str) -> BatchRecord:
        """Persist uploaded local monthly Excel source path for later merge."""

        batch = await self.repo.get(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        batch.artifacts["monthly_excel_path"] = monthly_excel_path
        batch.updated_at = datetime.now(UTC)
        await self.repo.save(batch)
        return batch

    async def request_merge(self, batch_id: str, req: MergeRequest) -> QueueTask:
        """Mark batch as merging and enqueue merge task."""

        batch = await self.repo.get(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        monthly_excel_path = req.monthly_excel_path or batch.artifacts.get("monthly_excel_path")
        if not monthly_excel_path:
            raise ValueError("monthly_excel_path is required or upload via /merge-source/local first")
        payload = req.model_dump()
        payload["monthly_excel_path"] = monthly_excel_path
        task = QueueTask.new(
            batch_id=batch_id,
            task_type=TaskType.MERGE_BATCH,
            payload=payload,
        )
        batch.status = BatchStatus.MERGING
        batch.updated_at = datetime.now(UTC)
        await self.repo.save(batch)
        await self.queue.enqueue(task)
        return task
