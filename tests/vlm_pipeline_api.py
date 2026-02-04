from __future__ import annotations

import argparse
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
    'zbon': (0, 0.8),
    'bar': (0.3, 0.6),
}
THRESHOLD_RECEIPT_RATIO = 2.0
THRESHOLD_CONFIDENCE = 0.8

def get_img_ratio(page: PageInfo) -> float:
    if page.width <= 0:
        return 0.0
    return page.height / page.width


def get_pdf_page_ratio(doc: fitz.Document) -> float | None:
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

def to_grayscale(
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


def get_archive_subdir_name(run_date: str, category: str) -> str:
    try:
        dt = datetime.strptime(run_date, "%d/%m/%Y")
        yymm = f"{dt.year % 100:02d}{dt.month:02d}"
    except ValueError:
        yymm = "0000"
    cat = category.strip().lower()
    if cat == "zbon":
        return f"{yymm}DO Bar Ausgabe"
    if cat == "bar":
        return f"{yymm}DO Z-Bon"
    return f"{yymm}DO {category}"


def get_compressed_pdf_name(category: str, extracted_kv: dict, run_date: str) -> str | None:
    cat = category.strip().lower()
    if cat == "zbon":
        try:
            dt = datetime.strptime(run_date, "%d/%m/%Y")
            return f"{dt.day:02d}_{dt.month:02d}_{dt.year} do.pdf"
        except ValueError:
            return None
    if cat == "bar":
        store_name = extracted_kv.get("store_name") or ""
        brutto = extracted_kv.get("brutto") or ""
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
    return None

def calc_proc_time(start: float) -> tuple[float, float]:
    time_now = time.perf_counter()
    return time_now, time_now - start

def run_pipeline(
    pdf_paths: Iterable[str],
    *,
    output_root: Path,
    backup_dest_dir: Path,
    category: str,
    run_date: str,
    results_dir: Path | None = None,
    results_path: Path | None = None,
    dpi: int = 300,
    prompt: str = DEFAULT_PROMPT,
    model: str = "qwen3-vl:4b",
    purpose="zbon",
) -> None:
    timestamp = int(datetime.now().timestamp())
    if results_dir is None:
        results_dir = output_root
    if results_dir.exists() and results_dir.is_file():
        print(f"--out_dir 不能是文件: {results_dir}")
        raise SystemExit(1)
    results_dir.mkdir(parents=True, exist_ok=True)
    if results_path is None:
        results_path = results_dir / f"results_{timestamp}.json"

    def _write_results(entry: dict[str, object]) -> None:
        print(f"results_path: {results_path}")
        results_path.parent.mkdir(parents=True, exist_ok=True)
        if not results_path.exists():
            with results_path.open("w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            print(f"[Results] Created: {results_path}")
        raw = results_path.read_text(encoding="utf-8").strip()
        if raw:
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("Results file is not a JSON list.")
        else:
            data = []
        data.append(entry)
        with results_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[Results] Appended entry: {entry.get('filename')}")

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
                pdf_ratio = get_pdf_page_ratio(doc)
        except Exception as exc:
            print(f"[PDF] 读取页数失败: {exc}")
            pdf_page_count = None
            pdf_ratio = None
            pdf_read_failed = True
        start = time.perf_counter()
        run_dir = output_root / pdf_path.stem
        extracted_kv = {llm_field: None for llm_field in prompts_dict[purpose]['fields']} # brutto, netto, store_name, run_date
        score_kv = {llm_field: None for llm_field in prompts_dict[purpose]['fields']}
        score_kv.pop("run_date", None)
        extracted_kv["run_date"] = run_date
        result_entry = {
            "filename": pdf_path.name,
            "result": extracted_kv,
            "score": score_kv,
            "category": category,
            "page_count": pdf_page_count,
        }
        print(extracted_kv)
        if pdf_read_failed:
            print("[PDF] 读取失败，跳过后续处理。")
            extracted_kv["brutto"] = None
            extracted_kv["netto"] = None
            score_kv["brutto"] = None
            score_kv["netto"] = None
            result_entry["proc_time"] = time.perf_counter() - start
            return result_entry
        
        if pdf_page_count == 1 and pdf_ratio is not None and pdf_ratio > THRESHOLD_RECEIPT_RATIO:
            file_type = "receipt"
            crop_y = [0,0.6]
        model_id = f"prebuilt-{file_type}"
        print(f"调用Azure: {pdf_path.name} | model {model_id}")
        time_now, result_entry["preproc_time"] = calc_proc_time(start)
        print("完成前处理，耗时: %.2f 秒" % result_entry["preproc_time"])
        azure_result = None
        if pdf_page_count is not None and pdf_page_count > 4:
            print(f"[PDF] 页数 {pdf_page_count} > 4，跳过 Azure 解析。")
            result_entry["skip_reason"] = "page_count>4"
        else:
            try:
                azure_result = analyze_document_with_azure(str(pdf_path), model_id=model_id)
            except Exception as exc:
                print(f"[Azure] 调用失败: {exc}")
                extracted_kv["brutto"] = None
                extracted_kv["netto"] = None
                score_kv["brutto"] = None
                score_kv["netto"] = None
                azure_result = None
        time_now, result_entry["proc_time"] = calc_proc_time(time_now)
        print("完成账单分析，耗时: %.2f 秒" % result_entry["proc_time"])
        if azure_result:
            store_name = azure_result.get("store_name").split('\n')[0].split('.')[0]
            value_map = {
                "brutto": azure_result.get("brutto"),
                "netto": azure_result.get("netto"),
                "store_name": store_name[0].upper() + store_name[1:],
                "total_tax": azure_result.get("total_tax"),
            }
            for key, value in value_map.items():
                if key in extracted_kv and value not in (None, "", "None"):
                    extracted_kv[key] = str(value)
            score_kv["brutto"] = azure_result.get("confidence_brutto")
            score_kv["netto"] = azure_result.get("confidence_netto")
            score_kv["store_name"] = azure_result.get("confidence_store_name")
            score_kv["total_tax"] = azure_result.get("confidence_total_tax")
        print(f"extracted_kv: {extracted_kv}")
        print("开始压缩备份PDF...")
        archive_dir = backup_dest_dir / get_archive_subdir_name(run_date, category)
        final_pdf = None
        try:
            name_suffix = str(time.time_ns())
            compressed_pdf = compress_image_only_pdf(
                pdf_path,
                dest_dir=archive_dir,
                dpi=dpi,
                name_suffix=name_suffix,
            )
            final_pdf = compressed_pdf
            new_name = get_compressed_pdf_name(category, extracted_kv, run_date)

            if new_name:
                target = compressed_pdf.parent / new_name
                if target.exists():
                    print(f"备份文件名已存在，保留原名: {compressed_pdf.name}")
                else:
                    compressed_pdf.rename(target)
                    final_pdf = target
                    print(f"备份文件已重命名: {target.name}")
        except Exception as exc:
            print(f"[WARN] 压缩备份PDF失败: {exc}")
            final_pdf = None
        if final_pdf is not None:
            result_entry["preview_path"] = str(final_pdf)
        print(f"=== 完成处理PDF: {pdf_path} ===\n")
        _ , result_entry["postproc_time"] = calc_proc_time(time_now)
        print("完成后处理，耗时: %.2f 秒" % result_entry["proc_time"])
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
            print(entry)
            _write_results(entry)

    print(f"检测结果已保存: {results_path}")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Azure invoice/receipt extraction with optional PDF backup compression."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="PDF file paths",
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dir",
        type=Path,
        help="Directory containing PDFs (added to inputs)",
    )
    parser.add_argument(
        "--dest-dir",
        dest="backup_dest_dir",
        type=Path,
        default=ROOT_DIR / "outputs" / "test_comp_pdf",
        help="Backup/compressed PDF output directory",
    )
    parser.add_argument(
        "--out_dir",
        dest="results_dir",
        type=Path,
        help="Results output directory",
    )
    parser.add_argument(
        "--cat",
        dest="category",
        required=True,
        help="Category name (e.g., BAR, ZBon)",
    )
    parser.add_argument(
        "--run_date",
        dest="run_date",
        default=datetime.now().strftime("%d/%m/%Y"),
        help="Run date in DD/MM/YYYY",
    )
    args = parser.parse_args()

    inputs = list(args.inputs)
    if args.input_dir is not None:
        if not args.input_dir.exists():
            print(f"目录不存在: {args.input_dir}")
            raise SystemExit(1)
        if not args.input_dir.is_dir():
            print(f"不是目录: {args.input_dir}")
            raise SystemExit(1)
        dir_pdfs = sorted(
            (p for p in args.input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
            key=lambda p: p.name,
        )
        inputs.extend(str(p) for p in dir_pdfs)
    print(inputs)
    if not inputs:
        print("必须提供至少一个 PDF 路径，或使用 --input-dir")
        raise SystemExit(1)

    run_pipeline(
        inputs,
        output_root=ROOT_DIR / "outputs" / "vlm_pipeline",
        backup_dest_dir=args.backup_dest_dir,
        category=args.category,
        run_date=args.run_date,
        results_dir=args.results_dir,
        dpi=300,
    )
