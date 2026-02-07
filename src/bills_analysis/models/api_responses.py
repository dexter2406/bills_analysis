from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from bills_analysis.models.common import ErrorInfo, InputFile, StrictModel
from bills_analysis.models.enums import BatchStatus, BatchType, TaskType
from bills_analysis.models.internal import BatchRecord, QueueTask
from bills_analysis.models.version import SCHEMA_VERSION


class BatchResponse(StrictModel):
    """Public batch response contract returned by API endpoints."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    batch_id: str
    type: BatchType
    status: BatchStatus
    run_date: str | None = None
    inputs: list[InputFile] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    review_rows_count: int = 0
    merge_output: dict[str, Any] = Field(default_factory=dict)
    error: ErrorInfo | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: BatchRecord) -> "BatchResponse":
        """Map internal storage model to stable public response shape."""

        error_obj = None
        if record.error:
            error_obj = ErrorInfo(code="BATCH_ERROR", message=record.error)
        return cls(
            batch_id=record.batch_id,
            type=record.batch_type,
            status=record.status,
            run_date=record.run_date,
            inputs=record.inputs,
            artifacts=record.artifacts,
            review_rows_count=len(record.review_rows),
            merge_output=record.merge_output,
            error=error_obj,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class BatchListResponse(StrictModel):
    """Paginated/list response wrapper for batch query endpoint."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    total: int
    items: list[BatchResponse]


class MergeTaskResponse(StrictModel):
    """Public merge-task response for async merge trigger endpoint."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    task_id: str
    batch_id: str
    task_type: TaskType
    created_at: datetime

    @classmethod
    def from_task(cls, task: QueueTask) -> "MergeTaskResponse":
        """Map internal task object to public task response."""

        return cls(
            task_id=task.task_id,
            batch_id=task.batch_id,
            task_type=task.task_type,
            created_at=task.created_at,
        )
