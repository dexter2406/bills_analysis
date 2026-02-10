from __future__ import annotations

import argparse
from pathlib import Path

from bills_analysis.services.merge_service import merge_office


def main() -> None:
    """CLI wrapper that merges office validated Excel via src merge service."""

    parser = argparse.ArgumentParser(description="Merge office validated Excel into monthly Excel.")
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
        help="Append rows instead of overwrite by Datum",
    )
    args = parser.parse_args()
    out_path = merge_office(
        args.validated_xlsx,
        args.monthly_xlsx,
        out_dir=args.out_dir,
        append=args.append,
    )
    print(f"[Excel] Merged and saved: {out_path}")


if __name__ == "__main__":
    main()
