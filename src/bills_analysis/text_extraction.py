"""Legacy OCR/text-layer extraction helpers (kept for reference)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import fitz  # PyMuPDF

from .contracts import BoundingBox, DocumentTokens, PageInfo, Token


def _words_to_tokens(words, page_no: int) -> List[Token]:
    tokens: List[Token] = []
    for word in words:
        # format: x0, y0, x1, y1, "text", block_no, line_no, word_no
        if len(word) < 5:
            continue
        x0, y0, x1, y1, text, *_ = word
        tokens.append(
            Token(
                text=str(text),
                confidence=1.0,
                page_no=page_no,
                bbox=BoundingBox(
                    x=float(x0),
                    y=float(y0),
                    width=float(x1 - x0),
                    height=float(y1 - y0),
                ),
            )
        )
    return tokens


def extract_text_layer_tokens(pdf_path: Path) -> DocumentTokens:
    """Extract tokens from the PDF text layer using PyMuPDF."""

    all_tokens: List[Token] = []
    with fitz.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            words = page.get_text("words") or []
            all_tokens.extend(_words_to_tokens(words, page_no=idx))
    return DocumentTokens(tokens=all_tokens)


def assess_token_coverage(tokens: DocumentTokens, page_width: float, page_height: float) -> float:
    """
    Approximate how much area tokens cover on a page (used to catch bad OCR).
    """

    if not tokens.tokens or page_width <= 0 or page_height <= 0:
        return 0.0
    total_area = page_width * page_height
    token_area = sum(t.bbox.width * t.bbox.height for t in tokens.tokens)
    return token_area / total_area


def is_ocr_anomalous(
    tokens: DocumentTokens,
    pages: Sequence[PageInfo],
    *,
    coverage_threshold: float = 0.002,
    min_tokens: int = 5,
    min_avg_conf: float = 0.3,
) -> bool:
    """
    Flag obviously bad OCR results to trigger text-layer fallback if available.

    Heuristics:
    - No tokens or too few tokens
    - Very low coverage relative to page area
    - Very low average confidence
    """

    if not tokens.tokens or len(tokens.tokens) < min_tokens:
        return True

    if pages:
        per_page_cov = [assess_token_coverage(tokens, p.width, p.height) for p in pages]
        avg_cov = sum(per_page_cov) / len(per_page_cov)
        if avg_cov < coverage_threshold:
            return True

    avg_conf = sum(t.confidence for t in tokens.tokens) / len(tokens.tokens)
    if avg_conf < min_avg_conf:
        return True

    return False
