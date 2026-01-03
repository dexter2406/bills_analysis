"""Text acquisition: image/PaddleOCR first, text-layer fallback when OCR looks bad."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import fitz  # PyMuPDF

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover - optional dependency
    PaddleOCR = None

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


def _get_paddle_client(lang: str):
    """Instantiate PaddleOCR client for a language; return None if unavailable."""

    if PaddleOCR is None:
        return None
    try:
        return PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    except Exception:
        return None


def _paddle_to_tokens(result, page_no: int) -> List[Token]:
    tokens: List[Token] = []
    for line in result:
        if len(line) < 2:
            continue
        box, info = line
        if not info or len(info) < 2:
            continue
        text, conf = info
        if not text:
            continue
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        tokens.append(
            Token(
                text=str(text),
                confidence=float(conf),
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


def ocr_tokens_paddle(
    image_paths: Iterable[Path],
    page_numbers: Iterable[int],
    pages: Sequence[PageInfo],
    primary_lang: str = "de",
    fallback_lang: str = "en",
) -> tuple[DocumentTokens, Dict[str, str]]:
    """
    OCR tokens using PaddleOCR. Try primary_lang; if anomalous, try fallback_lang.
    Returns tokens and metadata.
    """

    meta: Dict[str, str] = {
        "ocr_lang": primary_lang,
        "ocr_fallback_lang": fallback_lang,
        "ocr_error": "",
        "ocr_anomalous": "false",
    }

    client = _get_paddle_client(primary_lang)
    if client is None:
        meta["ocr_error"] = "paddleocr_not_available"
        return DocumentTokens(tokens=[]), meta

    tokens: List[Token] = []
    try:
        for img_path, page_no in zip(image_paths, page_numbers):
            result = client.ocr(str(img_path), cls=True)
            tokens.extend(_paddle_to_tokens(result, page_no))
    except Exception as exc:  # pragma: no cover - passthrough error
        meta["ocr_error"] = f"ocr_error:{exc}"
        return DocumentTokens(tokens=[]), meta

    doc_tokens = DocumentTokens(tokens=tokens)
    if is_ocr_anomalous(doc_tokens, pages):
        meta["ocr_anomalous"] = "true"
        if fallback_lang and fallback_lang != primary_lang:
            fb_client = _get_paddle_client(fallback_lang)
            if fb_client is not None:
                try:
                    fb_tokens: List[Token] = []
                    for img_path, page_no in zip(image_paths, page_numbers):
                        result = fb_client.ocr(str(img_path), cls=True)
                        fb_tokens.extend(_paddle_to_tokens(result, page_no))
                    fb_doc_tokens = DocumentTokens(tokens=fb_tokens)
                    if fb_doc_tokens.tokens:
                        doc_tokens = fb_doc_tokens
                        meta["ocr_lang"] = fallback_lang
                except Exception as exc:  # pragma: no cover - passthrough error
                    meta["ocr_error"] = f"ocr_fallback_error:{exc}"

    return doc_tokens, meta


def save_tokens(tokens: DocumentTokens, dest: Path) -> Optional[Path]:
    """Persist tokens to a JSON file for debugging."""

    if not tokens.tokens:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(tokens.model_dump_json(indent=2), encoding="utf-8")
    return dest


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
