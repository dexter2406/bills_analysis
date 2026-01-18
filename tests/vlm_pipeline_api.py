from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bills_analysis.preprocess import compress_image_only_pdf, preprocess_image
from bills_analysis.render import render_pdf_to_images
from bills_analysis.vlm import DEFAULT_PROMPT, prompts_dict
from bills_analysis.contracts import PageInfo
from bills_analysis.extract_by_azure_api import analyze_document_with_azure


crop_y_dict = {
    'beleg': (0, 0.8),
    'zbon': (0.3, 0.6),
}
THRESHOLD_RECEIPT_RATIO = 2.0
THRESHOLD_CONFIDENCE = 0.8

def get_img_ratio(page: PageInfo) -> float:
    if page.width <= 0:
        return 0.0
    return page.height / page.width

def _to_grayscale(
    src: Path,
    dest: Path,
    *,
    max_side: int | None = None,
    crop_y: tuple[float, float] | None = None,
) -> Path:
    # Only convert to grayscale; keep other preprocessing off to preserve details.
    return preprocess_image(
        src,
        dest,
        max_side=max_side,
        crop_y=crop_y,
        clahe=True,
        sharpen=True,
        sharpen_amount=0.5,
        autocontrast=False,
        denoise=False,
        binarize=False,
    )


def get_compressed_pdf_name(purpose: str, extracted_kv: dict) -> str | None:
    if purpose == "beleg":
        store_name = extracted_kv.get("Store_name") or ""
        brutto = extracted_kv.get("Brutto") or ""
        brutto_norm = str(brutto).strip().replace(",", ".")
        int_part, frac_part = brutto_norm, "00"
        if "." in brutto_norm:
            int_part, frac_part = brutto_norm.split(".", 1)
        int_part = "".join(ch for ch in int_part if ch.isdigit()) or "0"
        frac_part = "".join(ch for ch in frac_part if ch.isdigit()) or "00"
        safe_store = store_name.strip().replace("/", " ").replace("\\", " ").strip()
        if safe_store:
            return f"{safe_store} {int_part}_{frac_part}.pdf"
        return None
    if purpose == "zbon":
        today = datetime.now()
        return f"{today.day:02d}_{today.month:02d}_{today.year}.pdf"
    return None


def run_pipeline(
    pdf_paths: Iterable[str],
    *,
    output_root: Path,
    backup_dest_dir: Path,
    dpi: int = 300,
    prompt: str = DEFAULT_PROMPT,
    model: str = "qwen3-vl:4b",
    purpose="beleg",
) -> None:

    for pdf in pdf_paths:
        pdf_path = Path(pdf)
        if not pdf_path.exists():
            print(f"未找到PDF: {pdf_path}")
            continue
        file_type = "invoice"
        max_side = 1000
        print(f"\n=== 开始处理PDF: {pdf_path} ===")
        run_dir = output_root / pdf_path.stem
        pages = render_pdf_to_images(pdf_path, run_dir / "pages", dpi=dpi, skip_errors=False)
        extracted_kv = {llm_field: None for llm_field in prompts_dict[purpose]['fields']} # Brutto, Netto, etc.
        print(extracted_kv)
        if not pages:
            print(f"未渲染出页面，跳过: {pdf_path}")
            continue

        if len(pages) == 1 and get_img_ratio(pages[0]) > THRESHOLD_RECEIPT_RATIO:
            file_type = "receipt"
            crop_y = [0,0.6]
        model_id = f"prebuilt-{file_type}"
        print(f"调用Azure: {pdf_path.name} | model {model_id}")
        azure_result = analyze_document_with_azure(str(pdf_path), model_id=model_id)
        if azure_result:
            value_map = {
                "brutto": azure_result.get("brutto"),
                "netto": azure_result.get("netto"),
                "store_name": azure_result.get("store_name"),
            }
            for key, value in value_map.items():
                if key in extracted_kv and value not in (None, "", "None"):
                    extracted_kv[key] = str(value)
            score_brutto = azure_result.get("confidence_brutto")
            score_netto = azure_result.get("confidence_netto")
            if "score_brutto" in extracted_kv and extracted_kv["score_brutto"] in (None, "", "None"):
                extracted_kv["score_brutto"] = -1 if score_brutto is None else (1 if score_brutto >= THRESHOLD_CONFIDENCE else 0)
            if "score_netto" in extracted_kv and extracted_kv["score_netto"] in (None, "", "None"):
                extracted_kv["score_netto"] = -1 if score_netto is None else (1 if score_netto >= THRESHOLD_CONFIDENCE else 0)
        print(f"extracted_kv: {extracted_kv}")
        print("开始压缩备份PDF...")
        compressed_pdf = compress_image_only_pdf(
            pdf_path,
            dest_dir=backup_dest_dir,
            dpi=dpi,
        )
        new_name = get_compressed_pdf_name(purpose, extracted_kv)

        if new_name:
            target = compressed_pdf.parent / new_name
            if target.exists():
                print(f"备份文件名已存在，保留原名: {compressed_pdf.name}")
            else:
                compressed_pdf.rename(target)
                print(f"备份文件已重命名: {target.name}")
        print(f"=== 完成处理PDF: {pdf_path} ===\n")




if __name__ == "__main__":
    backup_dest_dir = ROOT_DIR / "outputs" / "test_comp_pdf"
    inputs = []
    for arg in sys.argv[1:]:
        if arg.startswith("--dest-dir="):
            backup_dest_dir = Path(arg.split("=", 1)[1].strip('"'))
        else:
            inputs.append(arg)
    if not inputs:
        print("用法: python tests/vlm_pipeline.py <pdf1> [pdf2 ...] [--dest-dir=PATH]")
        raise SystemExit(1)
    run_pipeline(
        inputs,
        output_root=ROOT_DIR / "outputs" / "vlm_pipeline",
        backup_dest_dir=backup_dest_dir,
        dpi=150,
    )
