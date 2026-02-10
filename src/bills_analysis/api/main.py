from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from bills_analysis.integrations.container import AppContainer, build_container
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
from bills_analysis.models.common import InputFile
from bills_analysis.models.enums import BatchType

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


def _parse_metadata_json(raw_metadata: str | None) -> dict[str, Any]:
    """Decode metadata JSON string into dictionary payload."""

    if raw_metadata is None or raw_metadata.strip() == "":
        return {}
    try:
        parsed = json.loads(raw_metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="metadata_json must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="metadata_json must be a JSON object")
    return parsed


def _validate_pdf_upload(file: UploadFile, *, field_name: str) -> None:
    """Validate filename extension and content type for uploaded PDF."""

    filename = (file.filename or "").strip()
    if not filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{field_name} must be PDF files")
    if file.content_type and "pdf" not in file.content_type.lower():
        raise HTTPException(status_code=400, detail=f"{field_name} must be PDF files")


async def _save_upload_file(
    file: UploadFile,
    *,
    dest_dir: Path,
    prefix: str,
    index: int,
) -> Path:
    """Persist one UploadFile to disk and return the saved file path."""

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "").name or f"{prefix}_{index:02d}.pdf"
    stem = Path(safe_name).stem or f"{prefix}_{index:02d}"
    dest_path = dest_dir / f"{index:02d}_{stem}.pdf"
    attempt = 1
    while dest_path.exists():
        dest_path = dest_dir / f"{index:02d}_{stem}_{attempt}.pdf"
        attempt += 1
    content = await file.read()
    dest_path.write_bytes(content)
    await file.close()
    return dest_path


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Lightweight health endpoint for liveness checks."""

    return {"status": "ok"}


@app.post("/v1/batches", response_model=BatchResponse)
async def create_batch(req: CreateBatchRequest) -> BatchResponse:
    """Create a batch and enqueue process task."""

    record = await container.service.create_batch(req)
    return BatchResponse.from_record(record)


@app.post(
    "/v1/batches/upload",
    response_model=CreateBatchUploadTaskResponse,
)
async def create_batch_upload(
    request: Request,
    type: str = Form(...),
    run_date: str | None = Form(None),
    metadata_json: str | None = Form(None),
    zbon_file: UploadFile | None = File(None),
    bar_files: list[UploadFile] = File(default_factory=list),
    office_files: list[UploadFile] = File(default_factory=list),
) -> CreateBatchUploadTaskResponse:
    """Create a batch from multipart upload and enqueue processing task."""

    metadata = _parse_metadata_json(metadata_json)

    try:
        upload_form = CreateBatchUploadForm(type=type, run_date=run_date, metadata=metadata)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc

    upload_root = Path("outputs") / "webapp" / "uploads" / str(uuid4())
    inputs: list[InputFile] = []
    form_data = await request.form()
    zbon_part_count = len(form_data.getlist("zbon_file"))

    if upload_form.type == BatchType.DAILY:
        if office_files:
            raise HTTPException(
                status_code=400,
                detail="office_files is not allowed when type=daily",
            )
        if zbon_part_count > 1:
            raise HTTPException(
                status_code=400,
                detail="daily upload requires exactly one zbon_file",
            )
        if zbon_file is None:
            raise HTTPException(
                status_code=400,
                detail="daily upload requires exactly one zbon_file",
            )
        _validate_pdf_upload(zbon_file, field_name="zbon_file")
        zbon_path = await _save_upload_file(
            zbon_file,
            dest_dir=upload_root / "zbon",
            prefix="zbon",
            index=1,
        )
        inputs.append(InputFile(path=str(zbon_path), category="zbon"))

        for index, file in enumerate(bar_files, start=1):
            _validate_pdf_upload(file, field_name="bar_files")
            bar_path = await _save_upload_file(
                file,
                dest_dir=upload_root / "bar",
                prefix="bar",
                index=index,
            )
            inputs.append(InputFile(path=str(bar_path), category="bar"))
    else:
        if not office_files:
            raise HTTPException(
                status_code=400,
                detail="office upload requires at least one office_files item",
            )
        if zbon_part_count > 0 or bar_files:
            raise HTTPException(
                status_code=400,
                detail="zbon_file/bar_files are not allowed when type=office",
            )
        for index, file in enumerate(office_files, start=1):
            _validate_pdf_upload(file, field_name="office_files")
            office_path = await _save_upload_file(
                file,
                dest_dir=upload_root / "office",
                prefix="office",
                index=index,
            )
            inputs.append(InputFile(path=str(office_path), category="office"))

    create_req = CreateBatchRequest(
        type=upload_form.type,
        run_date=upload_form.run_date,
        inputs=inputs,
        metadata=upload_form.metadata,
    )
    batch, task = await container.service.create_batch_with_task(create_req)
    return CreateBatchUploadTaskResponse.from_batch_and_task(batch=batch, task=task)


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

    # Start local HTTP server with env-configurable host and port.
    uvicorn.run(
        "bills_analysis.api.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    run()
