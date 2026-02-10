from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _get_field(result: dict[str, Any], key: str) -> Any:
    """Resolve field values with lower/capital/upper-case fallbacks."""

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
    """Convert number-like values into float with locale punctuation support."""

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
    """Convert reliability score value into float when possible."""

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
    """Split filenames into amount all-ok / partial / failed groups."""

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
    """Split filenames into reliability all-ok / partial / failed groups."""

    all_ok: list[str] = []
    partial_ok: list[str] = []
    failed: list[str] = []

    for item in items:
        filename = str(item.get("filename") or "")
        score_block = item.get("score") or item.get("result") or {}
        score_brutto = _to_score(_get_field(score_block, "brutto"))
        score_netto = _to_score(_get_field(score_block, "netto"))
        if score_brutto is None or score_netto is None:
            failed.append(filename)
            continue
        if score_brutto >= threshold and score_netto >= threshold:
            all_ok.append(filename)
        else:
            partial_ok.append(filename)
    return all_ok, partial_ok, failed


def resolve_results_path(json_path: Path | None, res_dir: Path | None) -> Path | None:
    """Resolve explicit JSON path or latest timestamped JSON in a results directory."""

    if json_path is not None:
        return json_path
    if res_dir is None:
        return None
    if not res_dir.exists() or not res_dir.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for path in res_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        stem = path.stem
        _prefix, sep, ts = stem.rpartition("_")
        if not sep or not ts.isdigit():
            continue
        candidates.append((int(ts), path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def load_report_items(path: Path, *, category: str | None = None) -> list[dict[str, Any]]:
    """Load report source items and optionally filter by exact category value."""

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("Empty results file.")
    if raw.lstrip().startswith("["):
        items = json.loads(raw)
    else:
        items = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if category is not None:
        items = [item for item in items if str(item.get("category") or "") == category]
    return items


def build_report_summary(
    items: list[dict[str, Any]],
    *,
    reliability_threshold: float,
) -> dict[str, Any]:
    """Build structured report metrics for amount and reliability checks."""

    all_ok, partial_ok, failed = summarize_results(items)
    rel_all_ok, rel_partial_ok, rel_failed = summarize_reliability(items, reliability_threshold)

    proc_times: list[tuple[float, str]] = []
    for item in items:
        filename = str(item.get("filename") or "")
        proc_time = _to_float(item.get("proc_time"))
        if proc_time is None:
            continue
        proc_times.append((proc_time, filename))
    proc_times.sort(key=lambda entry: entry[0], reverse=True)
    top_proc = proc_times[:3]

    total = len(items)
    denominator = total if total else 1
    return {
        "total": total,
        "amount": {
            "all_ok": all_ok,
            "partial_ok": partial_ok,
            "failed": failed,
            "summary_ratio": (
                f"{len(all_ok) / denominator:.0%} | "
                f"{len(partial_ok) / denominator:.0%} | "
                f"{len(failed) / denominator:.0%}"
            ),
        },
        "reliability": {
            "all_ok": rel_all_ok,
            "partial_ok": rel_partial_ok,
            "failed": rel_failed,
            "summary_ratio": (
                f"{len(rel_all_ok) / denominator:.0%} | "
                f"{len(rel_partial_ok) / denominator:.0%} | "
                f"{len(rel_failed) / denominator:.0%}"
            ),
        },
        "top_processing_times": top_proc,
    }
