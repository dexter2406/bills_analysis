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


def _matches_category(item: dict[str, Any], category: str | None) -> bool:
    if category is None:
        return True
    return str(item.get("category") or "") == category


def _resolve_json_path(json_path: Path | None, res_dir: Path | None) -> Path | None:
    if json_path is not None:
        return json_path
    if res_dir is None:
        return None
    if not res_dir.exists() or not res_dir.is_dir():
        return None
    candidates = []
    for path in res_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        stem = path.stem
        prefix, sep, ts = stem.rpartition("_")
        if not sep:
            continue
        if not ts.isdigit():
            continue
        candidates.append((int(ts), path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _print_group(title: str, files: list[str]) -> None:
    print(f"\n{title} ({len(files)}):")
    for name in files:
        print(f"- {name}")


def main() -> None:
    json_path: Path | None = None
    res_dir: Path | None = None
    category: str | None = None
    reliability_threshold = 0.8
    for arg in sys.argv[1:]:
        if arg.startswith("--json="):
            json_path = Path(arg.split("=", 1)[1].strip('"'))
        elif arg.startswith("--res-dir="):
            res_dir = Path(arg.split("=", 1)[1].strip('"'))
        elif arg.startswith("--cat="):
            category = arg.split("=", 1)[1].strip('"')
        elif arg.startswith("--reliability-threshold="):
            raw = arg.split("=", 1)[1].strip('"')
            try:
                reliability_threshold = float(raw)
            except ValueError:
                print(f"Invalid reliability threshold: {raw}")
                raise SystemExit(1)
        else:
            json_path = Path(arg)
    json_path = _resolve_json_path(json_path, res_dir)
    if json_path is None:
        print(
            "Usage: python tests/vlm_pipeline_report.py --json=PATH "
            "[--res-dir=PATH] [--cat=NAME] [--reliability-threshold=0.9]"
        )
        raise SystemExit(1)

    items = json.loads(json_path.read_text(encoding="utf-8"))
    if category is not None:
        items = [item for item in items if _matches_category(item, category)]
    all_ok, partial_ok, failed = summarize_results(items)
    rel_all_ok, rel_partial_ok, rel_failed = summarize_reliability(
        items,
        reliability_threshold,
    )

    total = len(items) if items else 1
    amount_summary = (
        f"Amount check: {len(all_ok) / total:.0%} | {len(partial_ok) / total:.0%} | {len(failed) / total:.0%}"
    )
    reliability_summary = (
        f"Reliability check: {len(rel_all_ok) / total:.0%} | {len(rel_partial_ok) / total:.0%} | {len(rel_failed) / total:.0%}"
    )
    print(amount_summary)
    print(reliability_summary)
    print("=" * 21)

    print(f"Amount Summary (cat={category or 'ALL'}):")
    print(f"All OK (brutto+netto are floats): {len(all_ok)}")
    print(f"Partial OK (only one float): {len(partial_ok)}")
    print(f"Failed (both missing): {len(failed)}")

    _print_group("All OK files", all_ok)
    _print_group("Partial OK files", partial_ok)
    _print_group("Failed files", failed)

    print(f"\nReliability Summary (cat={category or 'ALL'}, threshold={reliability_threshold}):")
    print(f"All reliable (both >= threshold): {len(rel_all_ok)}")
    print(f"Partially reliable (no null, some < threshold): {len(rel_partial_ok)}")
    print(f"Unreliable (any null score): {len(rel_failed)}")

    _print_group("Reliability All reliable files", rel_all_ok)
    _print_group("Reliability Partially reliable files", rel_partial_ok)
    _print_group("Reliability Unreliable files", rel_failed)

    proc_times: list[tuple[float, str]] = []
    for item in items:
        filename = str(item.get("filename") or "")
        proc_time = _to_float(item.get("proc_time"))
        if proc_time is None:
            continue
        proc_times.append((proc_time, filename))
    proc_times.sort(key=lambda entry: entry[0], reverse=True)
    top_proc = proc_times[:3]
    print("\nTop Processing Times:")
    if not top_proc:
        print("No proc_time values found.")
    else:
        for value, name in top_proc:
            print(f"- {name}: {value:.3f}s")


if __name__ == "__main__":
    main()
