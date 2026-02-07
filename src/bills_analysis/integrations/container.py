from __future__ import annotations

from dataclasses import dataclass

from bills_analysis.integrations.in_memory import InMemoryBatchRepository, InMemoryTaskQueue
from bills_analysis.integrations.local_backend import LocalPipelineBackend
from bills_analysis.services.batch_service import BatchService
from bills_analysis.workers.worker import BatchWorker


@dataclass
class AppContainer:
    """Runtime dependency container for API/service/worker wiring."""

    repo: InMemoryBatchRepository
    queue: InMemoryTaskQueue
    backend: LocalPipelineBackend
    service: BatchService
    worker: BatchWorker


def build_container() -> AppContainer:
    """Create default in-memory runtime container for local execution."""

    repo = InMemoryBatchRepository()
    queue = InMemoryTaskQueue()
    backend = LocalPipelineBackend()
    service = BatchService(repo, queue)
    worker = BatchWorker(repo=repo, queue=queue, backend=backend)
    return AppContainer(
        repo=repo,
        queue=queue,
        backend=backend,
        service=service,
        worker=worker,
    )
