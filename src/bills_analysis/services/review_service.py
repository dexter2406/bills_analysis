from __future__ import annotations

from pathlib import Path

from bills_analysis.integrations.excel_mapper_adapter import (
    map_daily_json_to_excel,
    map_office_json_to_excel,
)


def export_daily_review_excel(
    json_path: Path,
    *,
    excel_path: Path | None = None,
    config_path: Path | None = None,
) -> Path:
    """Export daily JSON results into review Excel with legacy-compatible mapping."""

    return map_daily_json_to_excel(
        json_path,
        excel_path=excel_path,
        config_path=config_path,
    )


def export_office_review_excel(
    json_path: Path,
    *,
    excel_path: Path | None = None,
    config_path: Path | None = None,
) -> Path:
    """Export office JSON results into review Excel with legacy-compatible mapping."""

    return map_office_json_to_excel(
        json_path,
        excel_path=excel_path,
        config_path=config_path,
    )
