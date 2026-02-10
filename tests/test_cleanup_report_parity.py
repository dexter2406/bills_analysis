from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from bills_analysis.services.maintenance_service import cleanup_outputs
from bills_analysis.services.report_service import build_report_summary, resolve_results_path


def test_cleanup_outputs_dry_run_and_delete_parity(monkeypatch) -> None:
    """Cleanup service should support dry-run listing and confirmed deletion."""

    root = Path("outputs") / "pytest_tmp" / str(uuid4())
    root.mkdir(parents=True, exist_ok=True)
    target = root / "to_delete.txt"
    target.write_text("x", encoding="utf-8")

    dry = cleanup_outputs(root=root, patterns=["*.txt"], confirm_delete=False)
    assert target in dry
    assert target.exists()

    called: dict[str, bool] = {}

    def fake_delete(paths, *, dry_run: bool):
        """Stub delete adapter to assert non-dry-run invocation semantics."""

        called["dry_run"] = dry_run
        return list(paths)

    monkeypatch.setattr("bills_analysis.services.maintenance_service.delete_paths", fake_delete)
    deleted = cleanup_outputs(root=root, patterns=["*.txt"], confirm_delete=True)
    assert called["dry_run"] is False
    assert target in deleted


def test_report_summary_parity() -> None:
    """Report summary should preserve amount and reliability grouping semantics."""

    items = [
        {"filename": "ok.pdf", "result": {"brutto": "10", "netto": "8"}, "score": {"brutto": 0.9, "netto": 0.9}},
        {"filename": "partial.pdf", "result": {"brutto": "10", "netto": None}, "score": {"brutto": 0.9, "netto": 0.9}},
        {"filename": "failed.pdf", "result": {"brutto": None, "netto": None}, "score": {"brutto": None, "netto": None}},
    ]
    summary = build_report_summary(items, reliability_threshold=0.8)
    assert summary["amount"]["all_ok"] == ["ok.pdf"]
    assert summary["amount"]["partial_ok"] == ["partial.pdf"]
    assert summary["amount"]["failed"] == ["failed.pdf"]


def test_resolve_results_path_latest_timestamp_parity() -> None:
    """Results path resolver should return the latest timestamped JSON file."""

    root = Path("outputs") / "pytest_tmp" / str(uuid4())
    root.mkdir(parents=True, exist_ok=True)
    old_path = root / "results_100.json"
    new_path = root / "results_200.json"
    old_path.write_text(json.dumps([]), encoding="utf-8")
    new_path.write_text(json.dumps([]), encoding="utf-8")

    resolved = resolve_results_path(None, root)
    assert resolved == new_path
