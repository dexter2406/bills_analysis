"""PDF rendering utilities."""

from __future__ import annotations

from pathlib import Path
from typing import List
import sys

import fitz  # PyMuPDF

from .contracts import PageInfo


def render_pdf_to_images(
    pdf_path: Path,
    out_dir: Path,
    dpi: int = 200,
    *,
    skip_errors: bool = True,
) -> List[PageInfo]:
    """
    Render each page of `pdf_path` to PNG images at the given DPI.

    Returns a list of PageInfo entries with image metadata and paths.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Rendering PDF: {pdf_path} -> {out_dir} (dpi={dpi})")

    with fitz.open(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages: List[PageInfo] = []

        total_pages = doc.page_count
        for idx, page in enumerate(doc, start=1):
            try:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
            except Exception as exc:
                if not skip_errors:
                    raise
                print(
                    f"Render failed for {pdf_path} page {idx}/{total_pages}: {exc}",
                    file=sys.stderr,
                )
                continue
            filename = f"page_{idx:02d}.png"
            dest = out_dir / filename
            pix.save(dest)
            print(f"Rendered page {idx}/{total_pages} -> {dest}")

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
