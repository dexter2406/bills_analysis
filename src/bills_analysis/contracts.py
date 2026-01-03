"""Schema definitions for `extraction.json` output."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Axis-aligned bounding box in pixel space."""

    x: float
    y: float
    width: float
    height: float


class PageInfo(BaseModel):
    """Metadata for each rendered page."""

    page_no: int = Field(..., ge=1)
    width: int
    height: int
    dpi: int
    source_path: Optional[str] = None
    preprocessed_path: Optional[str] = None


class Evidence(BaseModel):
    """Crop or overlay location for a field."""

    page_no: int = Field(..., ge=1)
    bbox: BoundingBox
    image_path: Optional[str] = None


class WarningItem(BaseModel):
    """Rule-based warnings that require human attention."""

    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    evidence_refs: List[str] = Field(default_factory=list)


class FieldCandidate(BaseModel):
    """Single extracted field with confidence and evidence."""

    name: str
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    page_no: Optional[int] = Field(default=None, ge=1)
    bbox: Optional[BoundingBox] = None
    evidence: Optional[Evidence] = None
    warnings: List[WarningItem] = Field(default_factory=list)
    candidates: List[str] = Field(
        default_factory=list,
        description="Top-N alternative values ordered by score.",
    )


class ExtractionResult(BaseModel):
    """Top-level output contract for a processed invoice."""

    document_name: str
    pages: List[PageInfo]
    fields: List[FieldCandidate]
    warnings: List[WarningItem] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="Paths to run artifacts (overlays, evidence, debug logs).",
    )
    meta: Dict[str, str] = Field(
        default_factory=dict,
        description="Pipeline metadata such as switches, versions, timestamps.",
    )


class Token(BaseModel):
    """Token with text, bbox, and confidence."""

    text: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    page_no: int = Field(..., ge=1)
    bbox: BoundingBox


class DocumentTokens(BaseModel):
    """Collection of tokens per document."""

    tokens: List[Token]
