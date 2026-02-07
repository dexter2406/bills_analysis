from __future__ import annotations
"""Contract tests for frozen API schema v1."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bills_analysis.models.api_requests import CreateBatchRequest, MergeRequest

def _get_test_client_and_app():
    """Lazily import FastAPI app to allow model-only tests without web deps."""

    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from bills_analysis.api.main import app

    return TestClient, app


def test_create_batch_request_valid() -> None:
    """CreateBatchRequest accepts valid daily payload."""

    req = CreateBatchRequest(
        type="daily",
        run_date="04/02/2026",
        inputs=[{"path": "a.pdf", "category": "bar"}],
        metadata={},
    )
    assert req.type == "daily"
    assert req.run_date == "04/02/2026"


def test_create_batch_request_alias_batch_type_is_accepted() -> None:
    """Backward-compatible `batch_type` alias should still parse."""

    req = CreateBatchRequest(
        batch_type="office",
        run_date="04/02/2026",
        inputs=[{"path": "b.pdf", "category": "office"}],
        metadata={},
    )
    assert req.type == "office"


def test_create_batch_request_invalid_run_date_rejected() -> None:
    """Invalid run_date format must be rejected by regex validation."""

    with pytest.raises(ValidationError):
        CreateBatchRequest(
            type="daily",
            run_date="2026-02-04",
            inputs=[{"path": "a.pdf", "category": "bar"}],
            metadata={},
        )


def test_create_batch_request_empty_inputs_rejected() -> None:
    """Empty inputs list must fail validation."""

    with pytest.raises(ValidationError):
        CreateBatchRequest(type="daily", run_date="04/02/2026", inputs=[], metadata={})


def test_create_batch_request_extra_field_rejected() -> None:
    """Unknown request field must fail because extra=forbid."""

    with pytest.raises(ValidationError):
        CreateBatchRequest(
            type="daily",
            run_date="04/02/2026",
            inputs=[{"path": "a.pdf", "category": "bar"}],
            metadata={},
            foo="bar",
        )


def test_create_batch_request_invalid_type_rejected() -> None:
    """Unknown batch type enum value must be rejected."""

    with pytest.raises(ValidationError):
        CreateBatchRequest(
            type="unknown",
            run_date="04/02/2026",
            inputs=[{"path": "a.pdf", "category": "bar"}],
            metadata={},
        )


def test_merge_request_invalid_mode_rejected() -> None:
    """Unknown merge mode must fail validation."""

    with pytest.raises(ValidationError):
        MergeRequest(mode="upsert")


def test_api_contract_v1_endpoints() -> None:
    """End-to-end API contract checks for v1 routes and response shapes."""

    TestClient, app = _get_test_client_and_app()
    with TestClient(app) as client:
        create_res = client.post(
            "/v1/batches",
            json={
                "type": "daily",
                "run_date": "04/02/2026",
                "inputs": [{"path": "a.pdf", "category": "bar"}],
                "metadata": {},
            },
        )
        assert create_res.status_code == 200
        created = create_res.json()
        assert created["schema_version"] == "v1"
        batch_id = created["batch_id"]

        get_res = client.get(f"/v1/batches/{batch_id}")
        assert get_res.status_code == 200
        got = get_res.json()
        assert got["schema_version"] == "v1"
        assert got["batch_id"] == batch_id

        review_res = client.put(
            f"/v1/batches/{batch_id}/review",
            json={"rows": [{"filename": "a.pdf", "result": {"brutto": "1.0"}}]},
        )
        assert review_res.status_code == 200
        reviewed = review_res.json()
        assert reviewed["review_rows_count"] == 1

        merge_res = client.post(
            f"/v1/batches/{batch_id}/merge",
            json={"mode": "overwrite", "monthly_excel_path": None, "metadata": {}},
        )
        assert merge_res.status_code == 200
        merged_task = merge_res.json()
        assert merged_task["schema_version"] == "v1"
        assert merged_task["batch_id"] == batch_id
        assert merged_task["task_type"] == "merge_batch"

        list_res = client.get("/v1/batches")
        assert list_res.status_code == 200
        list_body = list_res.json()
        assert list_body["schema_version"] == "v1"
        assert isinstance(list_body["items"], list)
        assert list_body["total"] >= 1


def _openapi_contract_subset(spec: dict) -> dict:
    """Extract only v1 paths and schema components for snapshot comparison."""

    paths = {}
    for path, methods in spec.get("paths", {}).items():
        if not path.startswith("/v1/batches") and path != "/healthz":
            continue
        paths[path] = methods
    components = spec.get("components", {}).get("schemas", {})
    return {"paths": paths, "schemas": components}


def test_openapi_contract_frozen_v1() -> None:
    """Current OpenAPI subset must match frozen baseline."""

    _, app = _get_test_client_and_app()
    baseline_path = Path("tests/openapi_v1_baseline.json")
    if not baseline_path.exists():
        pytest.skip(
            "Missing openapi baseline. Run: PYTHONPATH=src python scripts/export_openapi_v1.py"
        )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    current = _openapi_contract_subset(app.openapi())
    assert current == baseline
