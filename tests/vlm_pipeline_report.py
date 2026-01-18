from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def _get_field(result: dict[str, Any], key: str) -> Any:
    if key in result:
        return result[key]
    alt = key.capitalize()
    if alt in result:
        return result[alt]
    upper = key.upper()
    if upper in result:
        return result[upper]
    return None


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


def summarize_results(items: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    all_ok: list[str] = []
    partial_ok: list[str] = []
    failed: list[str] = []

    for item in items:
        filename = str(item.get("filename") or "")
        result = item.get("result") or {}
        brutto = _to_float(_get_field(result, "brutto"))
        netto = _to_float(_get_field(result, "netto"))
        if brutto is not None and netto is not None:
            all_ok.append(filename)
        elif brutto is None and netto is None:
            failed.append(filename)
        else:
            partial_ok.append(filename)

    return all_ok, partial_ok, failed


def summarize_reliability(
    items: list[dict[str, Any]],
    threshold: float,
) -> tuple[list[str], list[str], list[str]]:
    all_ok: list[str] = []
    partial_ok: list[str] = []
    failed: list[str] = []

    for item in items:
        filename = str(item.get("filename") or "")
        result = item.get("result") or {}
        score_brutto = _to_score(_get_field(result, "score_brutto"))
        score_netto = _to_score(_get_field(result, "score_netto"))
        if score_brutto is None or score_netto is None:
            failed.append(filename)
            continue
        if score_brutto >= threshold and score_netto >= threshold:
            all_ok.append(filename)
        else:
            partial_ok.append(filename)

    return all_ok, partial_ok, failed


def _print_group(title: str, files: list[str]) -> None:
    print(f"\n{title} ({len(files)}):")
    for name in files:
        print(f"- {name}")


def main() -> None:
    json_path: Path | None = None
    reliability_threshold = 0.9
    for arg in sys.argv[1:]:
        if arg.startswith("--json="):
            json_path = Path(arg.split("=", 1)[1].strip('"'))
        elif arg.startswith("--reliability-threshold="):
            raw = arg.split("=", 1)[1].strip('"')
            try:
                reliability_threshold = float(raw)
            except ValueError:
                print(f"Invalid reliability threshold: {raw}")
                raise SystemExit(1)
        else:
            json_path = Path(arg)
    if json_path is None:
        print(
            "Usage: python tests/vlm_pipeline_report.py --json=PATH "
            "[--reliability-threshold=0.9]"
        )
        raise SystemExit(1)

    items = json.loads(json_path.read_text(encoding="utf-8"))
    all_ok, partial_ok, failed = summarize_results(items)
    rel_all_ok, rel_partial_ok, rel_failed = summarize_reliability(
        items,
        reliability_threshold,
    )

    print("Amount Summary:")
    print(f"All OK (brutto+netto are floats): {len(all_ok)}")
    print(f"Partial OK (only one float): {len(partial_ok)}")
    print(f"Failed (both missing): {len(failed)}")

    _print_group("All OK files", all_ok)
    _print_group("Partial OK files", partial_ok)
    _print_group("Failed files", failed)

    print(f"\nReliability Summary (threshold={reliability_threshold}):")
    print(f"All reliable (both >= threshold): {len(rel_all_ok)}")
    print(f"Partially reliable (no null, some < threshold): {len(rel_partial_ok)}")
    print(f"Unreliable (any null score): {len(rel_failed)}")

    _print_group("Reliability All OK files", rel_all_ok)
    _print_group("Reliability Partial OK files", rel_partial_ok)
    _print_group("Reliability Failed files", rel_failed)


if __name__ == "__main__":
    main()
