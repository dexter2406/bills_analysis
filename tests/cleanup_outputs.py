from __future__ import annotations

import argparse
from pathlib import Path

from bills_analysis.cleanup import collect_paths, cleanup_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manually clean up output files or folders."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("outputs"),
        help="Root directory for glob patterns",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        default=[],
        help="Glob pattern under root (can be repeated)",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Absolute/relative path to delete (can be repeated)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete the matched paths",
    )
    args = parser.parse_args()

    targets = [Path(p) for p in args.path]
    if args.pattern:
        targets.extend(collect_paths(args.root, args.pattern))

    if not targets:
        print("No targets. Use --pattern or --path.")
        raise SystemExit(1)

    if not args.yes:
        print("Dry run. Use --yes to delete.")
    deleted = cleanup_paths(targets, dry_run=not args.yes)
    for path in deleted:
        print(f"- {path}")
    print(f"Total: {len(deleted)}")


if __name__ == "__main__":
    main()
