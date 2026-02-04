from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import PatternFill

def _load_results(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if raw.lstrip().startswith("["):
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        raise ValueError("Results JSON is not a list.")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    text = re.sub(r"[^\d,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _to_score(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        if re.match(r"^\d{2}/\d{2}/\d{4}$", text):
            return text
        if re.match(r"^\d{2}\.\d{2}\.\d{4}$", text):
            dt = datetime.strptime(text, "%d.%m.%Y")
            return dt.strftime("%d/%m/%Y")
    except ValueError:
        return None
    return None


def _load_thresholds(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"Empty thresholds file: {path}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Thresholds JSON must be an object.")
    return data


def _threshold_for(key: str, thresholds: dict[str, Any]) -> float:
    fields = thresholds.get("fields") or {}
    if isinstance(fields, dict) and key in fields:
        return float(fields[key])
    return float(thresholds.get("default", 0.8))


def _needs_review(
    result: dict[str, Any],
    score: dict[str, Any],
    thresholds: dict[str, Any],
) -> bool:
    fields_to_check = ["brutto", "netto", "store_name", "total_tax"]
    for field in fields_to_check:
        value = result.get(field)
        if value in (None, "", "None"):
            return True
        score_val = _to_score(score.get(field))
        # brutto/netto may be inferred from total_tax when score == -1
        if field in {"brutto", "netto"} and score_val == -1:
            score_val = _to_score(score.get("total_tax"))
            if score_val is None:
                return True
            if score_val < _threshold_for("total_tax", thresholds):
                return True
            continue
        if score_val is None:
            return True
        if score_val < _threshold_for(field, thresholds):
            return True
    return False


def _low_confidence_fields(
    result: dict[str, Any],
    score: dict[str, Any],
    thresholds: dict[str, Any],
) -> set[str]:
    low: set[str] = set()
    fields_to_check = ["brutto", "netto", "store_name", "total_tax"]
    for field in fields_to_check:
        value = result.get(field)
        if value in (None, "", "None"):
            low.add(field)
            continue
        score_val = _to_score(score.get(field))
        if field in {"brutto", "netto"} and score_val == -1:
            score_val = _to_score(score.get("total_tax"))
            if score_val is None or score_val < _threshold_for("total_tax", thresholds):
                low.add(field)
            continue
        if score_val is None:
            low.add(field)
            continue
        if score_val < _threshold_for(field, thresholds):
            low.add(field)
    return low


def _log_low_conf(
    filename: str,
    field: str,
    score_val: Any,
    threshold: float,
    *,
    reason: str,
) -> None:
    print(
        f"[LOW_CONF] file={filename} field={field} score={score_val} "
        f"threshold={threshold} reason={reason}"
    )


def build_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: OrderedDict[str, dict[str, Any]] = OrderedDict()
    thresholds_path = Path(__file__).with_name("score_thresholds.json")
    thresholds = _load_thresholds(thresholds_path)

    for item in items:
        category = str(item.get("category") or "").strip().lower()
        result = item.get("result") or {}
        score = item.get("score") or {}
        run_date = _normalize_date(result.get("run_date"))
        if not run_date:
            run_date = "UNKNOWN"
            print(f"[WARN] Missing run_date for {item.get('filename')}")

        row = rows.get(run_date)
        if row is None:
            row = {
                "Datum": run_date,
                "Umsatz Brutto": None,
                "Umsatz Netto": None,
                "需要校验": False,
                "Wie viel Rechnungen": 0,
                "_beleg_count": 0,
                "Ausgaben": [],
                "_low_headers": set(),
            }
            rows[run_date] = row

        brutto = _to_float(result.get("brutto"))
        netto = _to_float(result.get("netto"))
        store = str(result.get("store_name") or "").strip()
        filename = str(item.get("filename") or "")

        if category == "bar":
            if row["Umsatz Brutto"] is not None or row["Umsatz Netto"] is not None:
                print(f"[WARN] Duplicate BAR for {run_date}, overwriting Umsatz values.")
            row["Umsatz Brutto"] = brutto
            row["Umsatz Netto"] = netto
            low_fields = _low_confidence_fields(result, score, thresholds)
            if "brutto" in low_fields:
                row["_low_headers"].add("Umsatz Brutto")
                _log_low_conf(
                    filename,
                    "brutto",
                    score.get("brutto"),
                    _threshold_for("brutto", thresholds),
                    reason="below_threshold_or_missing",
                )
            if "netto" in low_fields:
                row["_low_headers"].add("Umsatz Netto")
                _log_low_conf(
                    filename,
                    "netto",
                    score.get("netto"),
                    _threshold_for("netto", thresholds),
                    reason="below_threshold_or_missing",
                )
        elif category == "beleg":
            row["_beleg_count"] += 1
            if len(row["Ausgaben"]) < 5:
                row["Ausgaben"].append(
                    {"Name": store, "Brutto": brutto, "Netto": netto}
                )
            else:
                print(f"[WARN] Beleg > 5 for {run_date}, truncating extra.")
            row["Wie viel Rechnungen"] = row["_beleg_count"]
            slot = row["_beleg_count"]
            low_fields = _low_confidence_fields(result, score, thresholds)
            if slot <= 5:
                if "store_name" in low_fields:
                    row["_low_headers"].add(f"Ausgabe {slot} Name")
                    _log_low_conf(
                        filename,
                        "store_name",
                        score.get("store_name"),
                        _threshold_for("store_name", thresholds),
                        reason="below_threshold_or_missing",
                    )
                if "brutto" in low_fields:
                    row["_low_headers"].add(f"Ausgabe {slot} Brutto")
                    _log_low_conf(
                        filename,
                        "brutto",
                        score.get("brutto"),
                        _threshold_for("brutto", thresholds),
                        reason="below_threshold_or_missing",
                    )
                if "netto" in low_fields:
                    row["_low_headers"].add(f"Ausgabe {slot} Netto")
                    _log_low_conf(
                        filename,
                        "netto",
                        score.get("netto"),
                        _threshold_for("netto", thresholds),
                        reason="below_threshold_or_missing",
                    )
        else:
            print(f"[WARN] Unknown category '{category}' for {item.get('filename')}")

        if _needs_review(result, score, thresholds):
            row["需要校验"] = True

    # Flatten to template-like columns for display
    output_rows: list[dict[str, Any]] = []
    for row in rows.values():
        out = {
            "Datum": row["Datum"],
            "Umsatz Brutto": row["Umsatz Brutto"],
            "Umsatz Netto": row["Umsatz Netto"],
            "需要校验": row["需要校验"],
            "Wie viel Rechnungen": row["Wie viel Rechnungen"],
        }
        for idx in range(5):
            key_base = f"Ausgabe {idx + 1}"
            if idx < len(row["Ausgaben"]):
                item = row["Ausgaben"][idx]
                out[f"{key_base} Name"] = item["Name"]
                out[f"{key_base} Brutto"] = item["Brutto"]
                out[f"{key_base} Netto"] = item["Netto"]
            else:
                out[f"{key_base} Name"] = None
                out[f"{key_base} Brutto"] = None
                out[f"{key_base} Netto"] = None
        output_rows.append(out)

    return output_rows


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
    items = _load_results(path)
    rows = build_rows(items)
    if not rows:
        print("No rows generated.")
        raise SystemExit(1)
    if len(rows) > 1:
        print(f"[WARN] Multiple dates found ({len(rows)}). Only the first row will be written.")

    first = rows[0]
    headers = list(first.keys())

    thresholds = _load_thresholds(Path(__file__).with_name("score_thresholds.json"))
    orange_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(headers)
    ws.append([first.get(h) for h in headers])

    # Highlight low-confidence fields in orange
    header_to_col = {name: idx + 1 for idx, name in enumerate(headers)}
    data_row_idx = 2
    low_headers = set()
    for item in items:
        result = item.get("result") or {}
        score = item.get("score") or {}
        run_date = _normalize_date(result.get("run_date")) or "UNKNOWN"
        if run_date != first.get("Datum"):
            continue
        category = str(item.get("category") or "").strip().lower()
        low_fields = _low_confidence_fields(result, score, thresholds)
        if not low_fields:
            continue
        if category == "bar":
            if "brutto" in low_fields:
                low_headers.add("Umsatz Brutto")
            if "netto" in low_fields:
                low_headers.add("Umsatz Netto")
        elif category == "beleg":
            # Use order in JSON to map Ausgabe slots (1..5)
            pass
    # Map beleg items to Ausgabe slots in order
    beleg_idx = 0
    for item in items:
        result = item.get("result") or {}
        score = item.get("score") or {}
        run_date = _normalize_date(result.get("run_date")) or "UNKNOWN"
        if run_date != first.get("Datum"):
            continue
        category = str(item.get("category") or "").strip().lower()
        if category != "beleg":
            continue
        beleg_idx += 1
        if beleg_idx > 5:
            continue
        low_fields = _low_confidence_fields(result, score, thresholds)
        if "store_name" in low_fields:
            low_headers.add(f"Ausgabe {beleg_idx} Name")
        if "brutto" in low_fields:
            low_headers.add(f"Ausgabe {beleg_idx} Brutto")
        if "netto" in low_fields:
            low_headers.add(f"Ausgabe {beleg_idx} Netto")

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
