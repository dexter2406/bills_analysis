"""Preprocessing utilities for rendered PDF pages."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, List, Sequence

import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageOps

from .contracts import PageInfo
from .render import render_pdf_to_images


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
    max_side: int | None = None,
    crop_y: Sequence[float] | None = None,
    clahe: bool = False,
    clahe_clip_limit: float = 2.0,
    clahe_tile_grid_size: tuple[int, int] = (8, 8),
    sharpen: bool = False,
    sharpen_amount: float = 0.5,
    autocontrast: bool = True,
    denoise: bool = False,
    binarize: bool = False,
    bin_thresh: int = 180,
) -> Path:
    """
    Basic preprocessing for scanned pages.

    Steps: grayscale -> optional crop -> optional resize -> optional denoise
    -> autocontrast -> optional binarization.
    Returns dest_path.

    Params:
    - max_side: 缩放目标最长边，超过则等比例缩小。
    - crop_y: 纵向裁剪区间（0.0-1.0），如 (0.3, 0.6)。
    - clahe: 是否使用CLAHE局部对比度增强。
    - clahe_clip_limit: CLAHE对比度限制。
    - clahe_tile_grid_size: CLAHE网格大小。
    - sharpen: 是否进行轻度锐化。
    - sharpen_amount: 锐化强度（0.0-1.0）。
    - autocontrast: 是否自动对比度拉伸。
    - denoise: 是否中值滤波降噪。
    - binarize: 是否二值化。
    - bin_thresh: 二值化阈值。
    """

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as img:
        work = img.convert("L")
        work = _apply_crop_y(work, crop_y)
        work = _apply_resize(work, max_side=max_side)
        if clahe:
            work = _apply_clahe(
                work,
                clip_limit=clahe_clip_limit,
                tile_grid_size=clahe_tile_grid_size,
            )
        if denoise:
            work = work.filter(ImageFilter.MedianFilter(size=3))
        if autocontrast:
            work = ImageOps.autocontrast(work)
        if sharpen:
            amount = max(0.0, min(1.0, float(sharpen_amount)))
            percent = max(1, int(200 * amount))
            work = work.filter(
                ImageFilter.UnsharpMask(radius=1, percent=percent, threshold=3)
            )
        if binarize:
            work = work.point(lambda p: 255 if p > bin_thresh else 0, mode="1")
        work.save(dest_path)
    return dest_path


def _apply_crop_y(work: Image.Image, crop_y: Sequence[float] | None) -> Image.Image:
    if crop_y is None:
        return work
    if len(crop_y) != 2:
        raise ValueError("crop_y must be a 2-item sequence of floats.")
    start = min(crop_y)
    end = max(crop_y)
    start = max(0.0, min(1.0, float(start)))
    end = max(0.0, min(1.0, float(end)))
    y0 = int(work.height * start)
    y1 = int(work.height * end)
    print(f"Crop Y range: {start:.2f}-{end:.2f} (pixels {y0}-{y1})")
    if y1 > y0:
        return work.crop((0, y0, work.width, y1))
    return work


def _apply_resize(work: Image.Image, max_side: int | None = None) -> Image.Image:
    if not max_side:
        return work
    max_dim = max(work.width, work.height)
    if max_dim <= max_side:
        return work
    scale = max_side / max_dim
    new_size = (
        max(1, int(work.width * scale)),
        max(1, int(work.height * scale)),
    )
    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    return work.resize(new_size, resample=resample)


def _apply_clahe(
    work: Image.Image,
    *,
    clip_limit: float,
    tile_grid_size: tuple[int, int],
) -> Image.Image:
    try:
        import cv2
        import numpy as np

        arr = np.array(work)
        clahe_op = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=tile_grid_size,
        )
        arr = clahe_op.apply(arr)
        return Image.fromarray(arr)
    except Exception as exc:
        print(f"CLAHE skipped: {exc}")
        return work


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


def compress_image_only_pdf(
    pdf_path: Path,
    *,
    dest_dir: Path,
    dpi: int = 150,
) -> Path:
    """
    If PDF has text layer, copy as-is to dest_dir.
    If PDF is image-only, render to grayscale images and re-pack into a new PDF.
    """

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_pdf = dest_dir / pdf_path.name

    if detect_pdf_has_text_layer(pdf_path):
        shutil.copy2(pdf_path, dest_pdf)
        print(f"PDF含文本层，已直接复制: {dest_pdf}")
        return dest_pdf

    before_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"纯图片PDF检测: {pdf_path}")
    print(f"压缩前大小: {before_mb:.2f} MB")

    temp_pages_dir = dest_dir / f".{pdf_path.stem}_pages"
    temp_gray_dir = dest_dir / f".{pdf_path.stem}_gray"
    if temp_pages_dir.exists():
        shutil.rmtree(temp_pages_dir, ignore_errors=True)
    if temp_gray_dir.exists():
        shutil.rmtree(temp_gray_dir, ignore_errors=True)

    pages = render_pdf_to_images(pdf_path, temp_pages_dir, dpi=dpi)
    if not pages:
        print("未渲染出页面，回退为原PDF复制。")
        shutil.copy2(pdf_path, dest_pdf)
        shutil.rmtree(temp_pages_dir, ignore_errors=True)
        return dest_pdf

    gray_paths: List[Path] = []
    for page in pages:
        if not page.source_path:
            continue
        src = Path(page.source_path)
        dest = temp_gray_dir / src.name
        preprocess_image(
            src,
            dest,
            max_side=2000,
            sharpen=True,
            sharpen_amount=0.3,
            autocontrast=False,
            denoise=False,
            binarize=False,
        )
        gray_paths.append(dest)

    if not gray_paths:
        print("未生成灰度图，回退为原PDF复制。")
        shutil.copy2(pdf_path, dest_pdf)
        shutil.rmtree(temp_pages_dir, ignore_errors=True)
        shutil.rmtree(temp_gray_dir, ignore_errors=True)
        return dest_pdf

    images: List[Image.Image] = []
    try:
        for path in gray_paths:
            images.append(Image.open(path).convert("L"))
        first, rest = images[0], images[1:]
        first.save(
            dest_pdf,
            "PDF",
            save_all=True,
            append_images=rest,
            resolution=dpi,
        )
    finally:
        for img in images:
            img.close()
        shutil.rmtree(temp_pages_dir, ignore_errors=True)
        shutil.rmtree(temp_gray_dir, ignore_errors=True)

    after_mb = dest_pdf.stat().st_size / (1024 * 1024)
    print(f"压缩后大小: {after_mb:.2f} MB")
    print(f"压缩结果已保存: {dest_pdf}")

    return dest_pdf
