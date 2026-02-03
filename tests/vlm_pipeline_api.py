from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bills_analysis.preprocess import compress_image_only_pdf, preprocess_image
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


def _get_pdf_page_ratio(doc: fitz.Document) -> float | None:
    if doc.page_count < 1:
        return None
    page = doc.load_page(0)
    rect = page.rect
    width = rect.width
    height = rect.height
    if page.rotation in (90, 270):
        width, height = height, width
    if width <= 0:
        return None
    return height / width

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
    category: str,
    results_dir: Path | None = None,
    dpi: int = 300,
    prompt: str = DEFAULT_PROMPT,
    model: str = "qwen3-vl:4b",
    purpose="beleg",
) -> None:
    timestamp = int(datetime.now().timestamp())
    if results_dir is None:
        results_dir = output_root
    if results_dir.exists() and results_dir.is_file():
        print(f"--out_dir 不能是文件: {results_dir}")
        raise SystemExit(1)
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / f"results_{timestamp}.json"

    results: list[dict[str, object]] = []

    def _write_results() -> None:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _process_one_pdf(idx: int, total: int, pdf: str) -> dict[str, object] | None:
        pdf_path = Path(pdf)
        if not pdf_path.exists():
            print(f"未找到PDF: {pdf_path}")
            return None
        file_type = "invoice"
        max_side = 1000
        print(f"\n=== 开始处理PDF ({idx}/{total}: {pdf_path} ===")
        pdf_read_failed = False
        try:
            with fitz.open(pdf_path) as doc:
                pdf_page_count = doc.page_count
                pdf_ratio = _get_pdf_page_ratio(doc)
        except Exception as exc:
            print(f"[PDF] 读取页数失败: {exc}")
            pdf_page_count = None
            pdf_ratio = None
            pdf_read_failed = True
        start = time.perf_counter()
        run_dir = output_root / pdf_path.stem
        # pages = render_pdf_to_images(pdf_path, run_dir / "pages", dpi=dpi, skip_errors=False)
        extracted_kv = {llm_field: None for llm_field in prompts_dict[purpose]['fields']} # Brutto, Netto, etc.
        result_entry = {
            "filename": pdf_path.name,
            "result": extracted_kv,
            "category": category,
        }
        print(extracted_kv)
        if pdf_read_failed:
            print("[PDF] 读取失败，跳过后续处理。")
            extracted_kv["brutto"] = None
            extracted_kv["netto"] = None
            extracted_kv["score_brutto"] = None
            extracted_kv["score_netto"] = None
            result_entry["proc_time"] = time.perf_counter() - start
            return result_entry
        # if not pages:
        #     print(f"未渲染出页面，跳过: {pdf_path}")
        #     result_entry["proc_time"] = time.perf_counter() - start
        #     results.append(result_entry)
        #     _write_results()
        #     continue
        
        if pdf_page_count == 1 and pdf_ratio is not None and pdf_ratio > THRESHOLD_RECEIPT_RATIO:
            file_type = "receipt"
            crop_y = [0,0.6]
        model_id = f"prebuilt-{file_type}"
        print(f"调用Azure: {pdf_path.name} | model {model_id}")
        print("完成前处理，耗时: %.2f 秒" % (time.perf_counter() - start))
        try:
            azure_result = analyze_document_with_azure(str(pdf_path), model_id=model_id)
        except Exception as exc:
            print(f"[Azure] 调用失败: {exc}")
            extracted_kv["brutto"] = None
            extracted_kv["netto"] = None
            extracted_kv["score_brutto"] = None
            extracted_kv["score_netto"] = None
            azure_result = None
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
            if extracted_kv.get('score_brutto') is None:
                extracted_kv['score_brutto'] = score_brutto if score_brutto not in ("", "None") else None
            if extracted_kv.get('score_netto') is None: 
                extracted_kv['score_netto'] = score_netto if score_netto not in ("", "None") else None
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
        result_entry["proc_time"] = time.perf_counter() - start
        return result_entry

    pdf_list = list(pdf_paths)
    total = len(pdf_list)
    if total == 0:
        print(f"检测结果已保存: {results_path}")
        return

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_process_one_pdf, idx, total, pdf)
            for idx, pdf in enumerate(pdf_list, start=1)
        ]
        for future in as_completed(futures):
            entry = future.result()
            if entry is None:
                continue
            results.append(entry)
            _write_results()

    print(f"检测结果已保存: {results_path}")




if __name__ == "__main__":
    backup_dest_dir = ROOT_DIR / "outputs" / "test_comp_pdf"
    input_dir: Path | None = None
    results_dir: Path | None = None
    category: str | None = None
    inputs = []
    for arg in sys.argv[1:]:
        if arg.startswith("--dest-dir="):
            backup_dest_dir = Path(arg.split("=", 1)[1].strip('"'))
        elif arg.startswith("--input-dir="):
            input_dir = Path(arg.split("=", 1)[1].strip('"'))
        elif arg.startswith("--out_dir="):
            results_dir = Path(arg.split("=", 1)[1].strip('"'))
        elif arg.startswith("--cat="):
            category = arg.split("=", 1)[1].strip('"')
        else:
            inputs.append(arg)
    if input_dir is not None:
        if not input_dir.exists():
            print(f"目录不存在: {input_dir}")
            raise SystemExit(1)
        if not input_dir.is_dir():
            print(f"不是目录: {input_dir}")
            raise SystemExit(1)
        dir_pdfs = sorted(
            (p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
            key=lambda p: p.name,
        )
        inputs.extend(str(p) for p in dir_pdfs)
    print(inputs)
    if not inputs:
        print(
            "用法: python tests/vlm_pipeline_api.py <pdf1> [pdf2 ...] "
            "[--input-dir=PATH] [--dest-dir=PATH] [--out_dir=PATH] [--cat=NAME]"
        )
        raise SystemExit(1)
    if not category:
        print("必须指定 --cat=NAME")
        raise SystemExit(1)
    run_pipeline(
        inputs,
        output_root=ROOT_DIR / "outputs" / "vlm_pipeline",
        backup_dest_dir=backup_dest_dir,
        category=category,
        results_dir=results_dir,
        dpi=150,
    )
