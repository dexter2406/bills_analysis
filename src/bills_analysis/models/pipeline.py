from __future__ import annotations

from typing import Any

from pydantic import Field

from bills_analysis.models.common import StrictModel


class ProcessDurations(StrictModel):
    """Processing duration metrics for one document pipeline run."""

    preproc_time: float | None = None
    proc_time: float | None = None
    postproc_time: float | None = None


class PipelineItemResult(StrictModel):
    """Structured pipeline output for one input PDF item."""

    filename: str
    category: str
    result: dict[str, Any] = Field(default_factory=dict)
    score: dict[str, Any] = Field(default_factory=dict)
    page_count: int | None = None
    process_duration: ProcessDurations = Field(default_factory=ProcessDurations)
    preview_path: str | None = None
    skip_reason: str | None = None
    errors: dict[str, str] = Field(default_factory=dict)


class PipelineBatchResult(StrictModel):
    """Aggregated pipeline output metadata for a batch execution."""

    results_path: str
    items: list[PipelineItemResult] = Field(default_factory=list)
