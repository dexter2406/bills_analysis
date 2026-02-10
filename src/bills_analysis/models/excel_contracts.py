from __future__ import annotations

from typing import Any

from pydantic import Field

from bills_analysis.models.common import StrictModel


class DailyReviewRow(StrictModel):
    """Canonical row payload for daily review Excel mapping."""

    datum: str
    umsatz_brutto: float | None = None
    umsatz_netto: float | None = None
    need_review: bool = False
    rechnung_count: int = 0
    ausgaben: list[dict[str, Any]] = Field(default_factory=list)


class OfficeReviewRow(StrictModel):
    """Canonical row payload for office review Excel mapping."""

    datum: str
    purpose: str | None = None
    sender: str | None = None
    brutto: float | None = None
    netto: float | None = None
    tax_id: str | None = None
    receiver_ok: bool | None = None
    need_review: bool = False
    preview_path: str | None = None


class MergeResult(StrictModel):
    """Normalized merge execution output."""

    output_path: str
    mode: str
    updated_rows: int = 0
    warnings: list[str] = Field(default_factory=list)
