"""PDF rendering utilities."""

from __future__ import annotations

from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from .contracts import PageInfo


def render_pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int = 200) -> List[PageInfo]:
    """
    Render each page of `pdf_path` to PNG images at the given DPI.

    Returns a list of PageInfo entries with image metadata and paths.
    """

    out_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages: List[PageInfo] = []

        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            filename = f"page_{idx:02d}.png"
            dest = out_dir / filename
            pix.save(dest)

            pages.append(
                PageInfo(
                    page_no=idx,
                    width=pix.width,
                    height=pix.height,
                    dpi=dpi,
                    source_path=str(dest),
                )
            )

    return pages
