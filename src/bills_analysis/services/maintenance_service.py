from __future__ import annotations

from pathlib import Path

from bills_analysis.integrations.filesystem_adapter import collect_paths, delete_paths


def cleanup_outputs(
    *,
    root: Path = Path("outputs"),
    patterns: list[str] | None = None,
    paths: list[Path] | None = None,
    confirm_delete: bool = False,
) -> list[Path]:
    """Collect and cleanup output paths with dry-run support."""

    targets = list(paths or [])
    if patterns:
        targets.extend(collect_paths(root, patterns))
    if not targets:
        raise ValueError("No targets. Use --pattern or --path.")
    return delete_paths(targets, dry_run=not confirm_delete)
