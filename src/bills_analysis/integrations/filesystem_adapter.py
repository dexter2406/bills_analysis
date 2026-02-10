from __future__ import annotations

from pathlib import Path
from typing import Iterable

from bills_analysis.cleanup import cleanup_paths


def collect_paths(root: Path, patterns: Iterable[str]) -> list[Path]:
    """Collect unique filesystem paths under root matching glob patterns."""

    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(root.glob(pattern))
    seen: set[Path] = set()
    uniq: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        uniq.append(path)
    return uniq


def delete_paths(paths: Iterable[Path], *, dry_run: bool = True) -> list[Path]:
    """Delete files/directories or perform dry-run listing via cleanup utility."""

    return cleanup_paths(paths, dry_run=dry_run)
