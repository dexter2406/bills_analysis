from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bills_analysis.models.common import InputFile
from bills_analysis.models.internal import BatchRecord


def _compress_pdf_for_archive(
    pdf_path: Path,
    *,
    dest_dir: Path,
    dpi: int,
    name_suffix: str,
) -> Path:
    """Compress and archive one source PDF via preprocess module."""

    from bills_analysis.preprocess import compress_image_only_pdf

    return compress_image_only_pdf(
        pdf_path,
        dest_dir=dest_dir,
        dpi=dpi,
        name_suffix=name_suffix,
    )


def _analyze_pdf_with_azure(
    pdf_path: Path,
    *,
    model_id: str,
    return_fields: bool,
) -> Any:
    """Run Azure DI extraction for one PDF via validated pipeline adapter."""

    from bills_analysis.extract_by_azure_api import analyze_document_with_azure

    return analyze_document_with_azure(
        str(pdf_path),
        model_id=model_id,
        return_fields=return_fields,
    )


def _clean_invoice_fields(fields_payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw invoice fields before Office semantic enrichment."""

    from bills_analysis.extract_by_azure_api import clean_invoice_json

    return clean_invoice_json(fields_payload)


def _extract_office_semantics(distilled_fields: dict[str, Any]) -> dict[str, Any]:
    """Extract Office category/sender/receiver semantic fields with AOAI."""

    from bills_analysis.extract_by_azure_api import extract_office_invoice_azure

    return extract_office_invoice_azure(distilled_fields)


class LocalPipelineBackend:
    """Local backend adapter that executes preprocess + extraction flow."""

    def __init__(self, *, root: Path | None = None) -> None:
        """Initialize output root for batch artifacts."""

        self.root = root or Path("outputs") / "webapp"

    async def process_batch(self, batch: BatchRecord) -> dict[str, Any]:
        """Process uploaded PDFs and emit result/review artifacts."""

        out_dir = self.root / batch.batch_id
        out_dir.mkdir(parents=True, exist_ok=True)
        archive_root = out_dir / "archive"
        archive_root.mkdir(parents=True, exist_ok=True)

        now = datetime.now(UTC).isoformat()
        results_path = out_dir / "results.json"
        review_path = out_dir / "review_rows.json"
        rows = [self._process_one_file(batch=batch, item=item, archive_root=archive_root) for item in batch.inputs]

        results_payload = {
            "batch_id": batch.batch_id,
            "batch_type": batch.batch_type.value,
            "run_date": batch.run_date,
            "inputs": [item.model_dump() for item in batch.inputs],
            "items": rows,
            "generated_at": now,
        }
        review_payload = [
            {
                "filename": row["filename"],
                "category": row["category"],
                "result": row["result"],
                "score": row["score"],
                "preview_path": row.get("preview_path"),
            }
            for row in rows
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
            "archive_root": str(archive_root),
        }

    def _process_one_file(
        self,
        *,
        batch: BatchRecord,
        item: InputFile,
        archive_root: Path,
    ) -> dict[str, Any]:
        """Run compression + extraction for one input file with safe fallbacks."""

        source_path = Path(item.path)
        category = (item.category or "office").lower()
        row: dict[str, Any] = {
            "filename": source_path.name,
            "category": category,
            "result": {"run_date": batch.run_date},
            "score": {},
        }

        if not source_path.exists():
            row["error"] = f"missing input file: {source_path}"
            return row

        try:
            compressed_path = _compress_pdf_for_archive(
                source_path,
                dest_dir=archive_root / category,
                dpi=300,
                name_suffix=batch.batch_id[:8],
            )
            row["preview_path"] = str(compressed_path)
        except Exception as exc:
            row["archive_error"] = str(exc)

        model_id = "prebuilt-invoice" if category == "office" else "prebuilt-receipt"
        try:
            if category == "office":
                azure_result, office_fields = _analyze_pdf_with_azure(
                    source_path,
                    model_id=model_id,
                    return_fields=True,
                )
                self._fill_office_row(row, azure_result, office_fields)
            else:
                azure_result = _analyze_pdf_with_azure(
                    source_path,
                    model_id=model_id,
                    return_fields=False,
                )
                self._fill_daily_row(row, azure_result)
        except Exception as exc:
            row["extract_error"] = str(exc)

        return row

    def _fill_daily_row(self, row: dict[str, Any], azure_result: dict[str, Any]) -> None:
        """Map Azure receipt fields into daily review row contract."""

        store_name = azure_result.get("store_name")
        if isinstance(store_name, str) and store_name.strip():
            row["result"]["store_name"] = store_name.splitlines()[0].strip()
        row["result"]["brutto"] = azure_result.get("brutto")
        row["result"]["netto"] = azure_result.get("netto")
        row["result"]["total_tax"] = azure_result.get("total_tax")
        row["score"]["store_name"] = azure_result.get("confidence_store_name")
        row["score"]["brutto"] = azure_result.get("confidence_brutto")
        row["score"]["netto"] = azure_result.get("confidence_netto")
        row["score"]["total_tax"] = azure_result.get("confidence_total_tax")

    def _fill_office_row(
        self,
        row: dict[str, Any],
        azure_result: dict[str, Any],
        office_fields: dict[str, Any],
    ) -> None:
        """Map Azure invoice fields and optional Office semantics into review row."""

        row["result"]["brutto"] = azure_result.get("brutto")
        row["result"]["netto"] = azure_result.get("netto")
        row["result"]["tax_id"] = azure_result.get("invoice_id")
        row["score"]["brutto"] = azure_result.get("confidence_brutto")
        row["score"]["netto"] = azure_result.get("confidence_netto")
        row["score"]["tax_id"] = azure_result.get("confidence_invoice_id")

        try:
            distilled = _clean_invoice_fields(office_fields)
            office_info = _extract_office_semantics(distilled)
            row["result"]["type"] = office_info.get("purpose")
            row["result"]["sender"] = office_info.get("sender")
            row["result"]["receiver"] = office_info.get("receiver")
        except Exception as exc:
            row["semantic_error"] = str(exc)

    async def merge_batch(self, batch: BatchRecord, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate merge summary artifact for current local adapter."""

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
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"merge_summary_path": str(merged_path)}
