"""
Backward-compatible transitional imports.

Use new modules instead:
- bills_analysis.models.api_requests
- bills_analysis.models.api_responses
- bills_analysis.models.internal
- bills_analysis.models.enums
"""

from bills_analysis.models.api_requests import (
    CreateBatchRequest,
    CreateBatchUploadForm,
    MergeRequest,
    SubmitReviewRequest,
)
from bills_analysis.models.api_responses import (
    BatchListResponse,
    BatchResponse,
    CreateBatchUploadTaskResponse,
    MergeTaskResponse,
)
from bills_analysis.models.common import ErrorInfo, InputFile
from bills_analysis.models.enums import BatchStatus, BatchType, TaskType
from bills_analysis.models.internal import BatchRecord, QueueTask
from bills_analysis.models.version import SCHEMA_VERSION

__all__ = [
    "BatchListResponse",
    "BatchRecord",
    "BatchResponse",
    "BatchStatus",
    "BatchType",
    "CreateBatchRequest",
    "CreateBatchUploadForm",
    "CreateBatchUploadTaskResponse",
    "ErrorInfo",
    "InputFile",
    "MergeRequest",
    "MergeTaskResponse",
    "QueueTask",
    "SCHEMA_VERSION",
    "SubmitReviewRequest",
    "TaskType",
]
