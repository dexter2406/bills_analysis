from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bills_analysis.models.internal import BatchRecord


class LocalPipelineBackend:
    """
    Minimal runnable backend adapter.

    This is intentionally simple: it writes placeholder artifacts so API/queue
    flow can be validated end-to-end without changing existing business scripts.
    """

    def __init__(self, *, root: Path | None = None) -> None:
        """Initialize output root for placeholder artifacts."""

        self.root = root or Path("outputs") / "webapp"

    async def process_batch(self, batch: BatchRecord) -> dict[str, Any]:
        """Generate placeholder process artifacts for one batch."""

        out_dir = self.root / batch.batch_id
        out_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC).isoformat()
        results_path = out_dir / "results.json"
        review_path = out_dir / "review_rows.json"

        results_payload = {
            "batch_id": batch.batch_id,
            "batch_type": batch.batch_type.value,
            "run_date": batch.run_date,
            "inputs": [item.model_dump() for item in batch.inputs],
            "generated_at": now,
            "note": "webapp skeleton output; replace with real pipeline adapter",
        }
        review_payload = [
            {
                "filename": Path(item.path).name,
                "category": item.category,
                "result": {},
                "score": {},
            }
            for item in batch.inputs
        ]
        results_path.write_text(
            json.dumps(results_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        review_path.write_text(
            json.dumps(review_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "result_json_path": str(results_path),
            "review_json_path": str(review_path),
            "archive_root": str(out_dir / "archive"),
        }

    async def merge_batch(self, batch: BatchRecord, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate placeholder merge summary artifact."""

        out_dir = self.root / batch.batch_id
        out_dir.mkdir(parents=True, exist_ok=True)
        merged_path = out_dir / "merge_summary.json"
        merged_path.write_text(
            json.dumps(
                {
                    "batch_id": batch.batch_id,
                    "mode": payload.get("mode", "overwrite"),
                    "monthly_excel_path": payload.get("monthly_excel_path"),
                    "review_rows_count": len(batch.review_rows),
                    "generated_at": datetime.now(UTC).isoformat(),
                    "note": "webapp skeleton merge output; replace with real merge adapter",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"merge_summary_path": str(merged_path)}
