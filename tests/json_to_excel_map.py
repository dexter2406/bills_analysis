from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import PatternFill

from bills_analysis.excel_ops import (
    build_rows,
    compute_low_headers,
    low_confidence_fields,
    threshold_for,
    to_score,
)


def load_results(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if raw.lstrip().startswith("["):
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        raise ValueError("Results JSON is not a list.")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def load_thresholds(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"Empty thresholds file: {path}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Thresholds JSON must be an object.")
    return data


def log_low_conf(item: dict[str, Any], thresholds: dict[str, Any]) -> None:
    result = item.get("result") or {}
    score = item.get("score") or {}
    low_fields = low_confidence_fields(result, score, thresholds)
    if not low_fields:
        return
    filename = str(item.get("filename") or "")
    for field in sorted(low_fields):
        raw_score = score.get(field)
        score_val = to_score(raw_score)
        if field in {"brutto", "netto"} and score_val == -1:
            raw_score = score.get("total_tax")
            threshold = threshold_for("total_tax", thresholds)
        else:
            threshold = threshold_for(field, thresholds)
        print(
            f"[LOW_CONF] file={filename} field={field} score={raw_score} "
            f"threshold={threshold} reason=below_threshold_or_missing"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Map results JSON to a one-row Excel file."
    )
    parser.add_argument("json_path", type=Path, help="Path to results JSON")
    parser.add_argument(
        "excel_path",
        type=Path,
        nargs="?",
        help="Output Excel path (default: same dir/name as JSON)",
    )
    args = parser.parse_args()

    path = args.json_path
    out_path = args.excel_path or path.with_suffix(".xlsx")
    items = load_results(path)
    thresholds_path = Path(__file__).with_name("score_thresholds.json")
    thresholds = load_thresholds(thresholds_path)
    for item in items:
        log_low_conf(item, thresholds)
    rows = build_rows(items, thresholds)
    if not rows:
        print("No rows generated.")
        raise SystemExit(1)
    if len(rows) > 1:
        print(f"[WARN] Multiple dates found ({len(rows)}). Only the first row will be written.")

    first = rows[0]
    headers = list(first.keys())

    thresholds = load_thresholds(Path(__file__).with_name("score_thresholds.json"))
    orange_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(headers)
    ws.append([first.get(h) for h in headers])

    # Highlight low-confidence fields in orange
    header_to_col = {name: idx + 1 for idx, name in enumerate(headers)}
    data_row_idx = 2
    low_headers = compute_low_headers(
        items,
        thresholds,
        first.get("Datum") or "UNKNOWN",
    )

    for header in low_headers:
        col = header_to_col.get(header)
        if col is not None:
            ws.cell(row=data_row_idx, column=col).fill = orange_fill
    if low_headers:
        col = header_to_col.get("需要校验")
        if col is not None:
            ws.cell(row=data_row_idx, column=col).fill = orange_fill

    wb.save(out_path)
    print(f"[Excel] Written: {out_path}")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
