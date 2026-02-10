from __future__ import annotations

import argparse
from pathlib import Path

from bills_analysis.services.maintenance_service import cleanup_outputs


def main() -> None:
    """CLI wrapper that executes output cleanup via src maintenance service."""

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
    deleted = cleanup_outputs(
        root=args.root,
        patterns=args.pattern,
        paths=targets,
        confirm_delete=args.yes,
    )
    if not args.yes:
        print("Dry run. Use --yes to delete.")
    for path in deleted:
        print(f"- {path}")
    print(f"Total: {len(deleted)}")


if __name__ == "__main__":
    main()
