"""Preprocessing utilities for rendered PDF pages."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageOps

from .contracts import PageInfo


def detect_pdf_has_text_layer(pdf_path: Path, sample_pages: int = 2) -> bool:
    """
    Heuristic: check first N pages for text. Returns True if any text found.
    """

    with fitz.open(pdf_path) as doc:
        for page in doc[:sample_pages]:
            text = page.get_text("text").strip()
            if text:
                return True
    return False


def preprocess_image(
    image_path: Path,
    dest_path: Path,
    *,
    autocontrast: bool = True,
    denoise: bool = True,
    binarize: bool = True,
    bin_thresh: int = 180,
) -> Path:
    """
    Basic preprocessing for scanned pages.

    Steps: grayscale -> optional denoise -> autocontrast -> optional binarization.
    Returns dest_path.
    """

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as img:
        work = img.convert("L")
        if denoise:
            work = work.filter(ImageFilter.MedianFilter(size=3))
        if autocontrast:
            work = ImageOps.autocontrast(work)
        if binarize:
            work = work.point(lambda p: 255 if p > bin_thresh else 0, mode="1")
        work.save(dest_path)
    return dest_path


def preprocess_pages(
    pages: Iterable[PageInfo],
    *,
    output_dir: Path,
    enable: bool = True,
    binarize: bool = True,
    bin_thresh: int = 180,
) -> List[PageInfo]:
    """
    Apply preprocessing to a collection of PageInfo entries.

    Returns a new list of PageInfo with preprocessed_path set (or unchanged if disabled).
    """

    processed: List[PageInfo] = []
    if not enable:
        return list(pages)

    for page in pages:
        if not page.source_path:
            processed.append(page)
            continue
        src = Path(page.source_path)
        dest = output_dir / f"page_{page.page_no:02d}.preproc.png"
        preprocess_image(
            src,
            dest,
            binarize=binarize,
            bin_thresh=bin_thresh,
        )
        processed.append(
            PageInfo(
                page_no=page.page_no,
                width=page.width,
                height=page.height,
                dpi=page.dpi,
                source_path=page.source_path,
                preprocessed_path=str(dest),
            )
        )
    return processed
