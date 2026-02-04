from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any


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


def build_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for item in items:
        category = str(item.get("category") or "").strip().lower()
        result = item.get("result") or {}
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
                "Wie viel Rechnungen": 0,
                "_beleg_count": 0,
                "Ausgaben": [],
            }
            rows[run_date] = row

        brutto = _to_float(result.get("brutto"))
        netto = _to_float(result.get("netto"))
        store = str(result.get("store_name") or "").strip()

        if category == "bar":
            if row["Umsatz Brutto"] is not None or row["Umsatz Netto"] is not None:
                print(f"[WARN] Duplicate BAR for {run_date}, overwriting Umsatz values.")
            row["Umsatz Brutto"] = brutto
            row["Umsatz Netto"] = netto
        elif category == "beleg":
            row["_beleg_count"] += 1
            if len(row["Ausgaben"]) < 5:
                row["Ausgaben"].append(
                    {"Name": store, "Brutto": brutto, "Netto": netto}
                )
            else:
                print(f"[WARN] Beleg > 5 for {run_date}, truncating extra.")
            row["Wie viel Rechnungen"] = row["_beleg_count"]
        else:
            print(f"[WARN] Unknown category '{category}' for {item.get('filename')}")

    # Flatten to template-like columns for display
    output_rows: list[dict[str, Any]] = []
    for row in rows.values():
        out = {
            "Datum": row["Datum"],
            "Umsatz Brutto": row["Umsatz Brutto"],
            "Umsatz Netto": row["Umsatz Netto"],
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
    if len(sys.argv) < 2:
        print("Usage: python tests/json_to_excel_map.py <results.json>")
        raise SystemExit(1)
    path = Path(sys.argv[1])
    items = _load_results(path)
    rows = build_rows(items)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
