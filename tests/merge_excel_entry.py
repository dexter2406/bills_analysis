from __future__ import annotations

import argparse
from pathlib import Path

from bills_analysis.services.merge_service import merge_daily, merge_office


def main() -> None:
    """CLI entrypoint for daily/office Excel merge through src merge service."""

    parser = argparse.ArgumentParser(
        description="Entry point for merging validated Excel into monthly Excel."
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "office"],
        required=True,
        help="Merge mode: daily (zbon/bar) or office",
    )
    parser.add_argument("validated_xlsx", type=Path, help="Validated Excel")
    parser.add_argument("monthly_xlsx", type=Path, help="Monthly Excel")
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        type=Path,
        help="Output directory (default: same as monthly_xlsx)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append rows instead of overwrite by Datum (office only)",
    )
    args = parser.parse_args()

    if args.mode == "daily":
        out_path = merge_daily(args.validated_xlsx, args.monthly_xlsx, out_dir=args.out_dir)
    else:
        out_path = merge_office(
            args.validated_xlsx,
            args.monthly_xlsx,
            out_dir=args.out_dir,
            append=args.append,
        )
    print(f"[Excel] Merged and saved: {out_path}")


if __name__ == "__main__":
    main()
