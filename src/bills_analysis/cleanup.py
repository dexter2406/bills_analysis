from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable


def collect_paths(root: Path, patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(root.glob(pattern))
    # Deduplicate while preserving order
    seen = set()
    uniq: list[Path] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def cleanup_paths(paths: Iterable[Path], *, dry_run: bool = True) -> list[Path]:
    deleted: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if dry_run:
            deleted.append(path)
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        deleted.append(path)
    return deleted
