from __future__ import annotations

import argparse
from pathlib import Path

from merge_daily_excel import merge_daily
from merge_office_excel import merge_office


def main() -> None:
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
        merge_daily(args.validated_xlsx, args.monthly_xlsx, out_dir=args.out_dir)
    else:
        merge_office(
            args.validated_xlsx,
            args.monthly_xlsx,
            out_dir=args.out_dir,
            append=args.append,
        )


if __name__ == "__main__":
    main()
