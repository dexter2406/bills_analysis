from __future__ import annotations

from enum import Enum


class BatchType(str, Enum):
    """Supported high-level batch categories."""

    DAILY = "daily"  # Daily settlement workflow.
    OFFICE = "office"  # Office expense/invoice workflow.


class BatchStatus(str, Enum):
    """Lifecycle status for a batch processing job."""

    QUEUED = "queued"  # Waiting in queue.
    RUNNING = "running"  # Extraction/processing is running.
    REVIEW_READY = "review_ready"  # Ready for human review.
    MERGING = "merging"  # Merge task is in progress.
    MERGED = "merged"  # Merge task completed successfully.
    FAILED = "failed"  # Processing or merge failed.


class TaskType(str, Enum):
    """Queue task types handled by the worker."""

    PROCESS_BATCH = "process_batch"  # Build extraction/review artifacts.
    MERGE_BATCH = "merge_batch"  # Merge reviewed data to target output.
