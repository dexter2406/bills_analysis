from __future__ import annotations

import argparse
from pathlib import Path

from bills_analysis.services.merge_service import merge_daily


def main() -> None:
    """CLI wrapper that merges daily validated Excel via src merge service."""

    parser = argparse.ArgumentParser(
        description="Merge a validated one-row Excel into a monthly Excel by Datum."
    )
    parser.add_argument("validated_xlsx", type=Path, help="One-row validated Excel")
    parser.add_argument("monthly_xlsx", type=Path, help="Monthly full Excel")
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        type=Path,
        help="Output directory (default: same as monthly_xlsx)",
    )
    args = parser.parse_args()
    out_path = merge_daily(args.validated_xlsx, args.monthly_xlsx, out_dir=args.out_dir)
    print(f"[Excel] Merged and saved: {out_path}")


if __name__ == "__main__":
    main()
