from __future__ import annotations

import argparse
from pathlib import Path

from bills_analysis.services.report_service import (
    build_report_summary,
    load_report_items,
    resolve_results_path,
)


def _print_group(title: str, files: list[str]) -> None:
    """Print one grouped filename list in legacy report output format."""

    print(f"\n{title} ({len(files)}):")
    for name in files:
        print(f"- {name}")



def main() -> None:
    """CLI wrapper that builds extraction report via src report service."""

    parser = argparse.ArgumentParser(
        description=(
            "Usage: python tests/vlm_pipeline_report.py --json=PATH "
            "[--res-dir=PATH] [--cat=NAME] [--reliability-threshold=0.9]"
        )
    )
    parser.add_argument("json_path", nargs="?", type=Path)
    parser.add_argument("--json", dest="json_opt", type=Path)
    parser.add_argument("--res-dir", dest="res_dir", type=Path)
    parser.add_argument("--cat", dest="category", type=str)
    parser.add_argument(
        "--reliability-threshold",
        dest="reliability_threshold",
        type=float,
        default=0.8,
    )
    args = parser.parse_args()

    json_path = resolve_results_path(args.json_opt or args.json_path, args.res_dir)
    if json_path is None:
        print(
            "Usage: python tests/vlm_pipeline_report.py --json=PATH "
            "[--res-dir=PATH] [--cat=NAME] [--reliability-threshold=0.9]"
        )
        raise SystemExit(1)

    items = load_report_items(json_path, category=args.category)
    summary = build_report_summary(items, reliability_threshold=args.reliability_threshold)

    amount = summary["amount"]
    reliability = summary["reliability"]

    print(f"Amount check: {amount['summary_ratio']}")
    print(f"Reliability check: {reliability['summary_ratio']}")
    print("=" * 21)

    print(f"Amount Summary (cat={args.category or 'ALL'}):")
    print(f"All OK (brutto+netto are floats): {len(amount['all_ok'])}")
    print(f"Partial OK (only one float): {len(amount['partial_ok'])}")
    print(f"Failed (both missing): {len(amount['failed'])}")

    _print_group("All OK files", amount["all_ok"])
    _print_group("Partial OK files", amount["partial_ok"])
    _print_group("Failed files", amount["failed"])

    print(
        f"\nReliability Summary (cat={args.category or 'ALL'}, "
        f"threshold={args.reliability_threshold}):"
    )
    print(f"All reliable (both >= threshold): {len(reliability['all_ok'])}")
    print(f"Partially reliable (no null, some < threshold): {len(reliability['partial_ok'])}")
    print(f"Unreliable (any null score): {len(reliability['failed'])}")

    _print_group("Reliability All reliable files", reliability["all_ok"])
    _print_group("Reliability Partially reliable files", reliability["partial_ok"])
    _print_group("Reliability Unreliable files", reliability["failed"])

    print("\nTop Processing Times:")
    top_proc = summary["top_processing_times"]
    if not top_proc:
        print("No proc_time values found.")
    else:
        for value, name in top_proc:
            print(f"- {name}: {value:.3f}s")


if __name__ == "__main__":
    main()
