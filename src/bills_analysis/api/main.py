from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import suppress

from fastapi import FastAPI, HTTPException

from bills_analysis.integrations.container import AppContainer, build_container
from bills_analysis.models.api_requests import CreateBatchRequest, MergeRequest, SubmitReviewRequest
from bills_analysis.models.api_responses import BatchListResponse, BatchResponse, MergeTaskResponse

container: AppContainer = build_container()


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown lifecycle and inline worker task."""

    run_inline_worker = os.getenv("RUN_INLINE_WORKER", "true").lower() == "true"
    if run_inline_worker:
        app.state.worker_task = asyncio.create_task(container.worker.run_forever())
    try:
        yield
    finally:
        task = getattr(app.state, "worker_task", None)
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="bills_analysis webapp skeleton", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Lightweight health endpoint for liveness checks."""

    return {"status": "ok"}


@app.post("/v1/batches", response_model=BatchResponse)
async def create_batch(req: CreateBatchRequest) -> BatchResponse:
    """Create a batch and enqueue process task."""

    record = await container.service.create_batch(req)
    return BatchResponse.from_record(record)


@app.get("/v1/batches", response_model=BatchListResponse)
async def list_batches(limit: int = 100) -> BatchListResponse:
    """List batches with stable v1 response envelope."""

    records = await container.service.list_batches(limit=limit)
    items = [BatchResponse.from_record(r) for r in records]
    return BatchListResponse(total=len(items), items=items)


@app.get("/v1/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: str) -> BatchResponse:
    """Fetch one batch by id."""

    batch = await container.service.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return BatchResponse.from_record(batch)


@app.put("/v1/batches/{batch_id}/review", response_model=BatchResponse)
async def submit_review(batch_id: str, req: SubmitReviewRequest) -> BatchResponse:
    """Store human-reviewed rows for a batch."""

    try:
        record = await container.service.save_review(batch_id, req)
        return BatchResponse.from_record(record)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="batch not found") from exc


@app.post("/v1/batches/{batch_id}/merge", response_model=MergeTaskResponse)
async def queue_merge(batch_id: str, req: MergeRequest) -> MergeTaskResponse:
    """Enqueue merge task for a reviewed batch."""

    try:
        task = await container.service.request_merge(batch_id, req)
        return MergeTaskResponse.from_task(task)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="batch not found") from exc


def run() -> None:
    """Local API entrypoint used by script/console command."""

    import uvicorn

    uvicorn.run(
        "bills_analysis.api.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    run()
