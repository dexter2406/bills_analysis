from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Iterable

from vlm_pipeline_api import ROOT_DIR, run_pipeline


def _collect_pdfs(paths: Iterable[str], input_dir: Path | None) -> list[str]:
    pdfs = list(paths)
    if input_dir is None:
        return pdfs
    if not input_dir.exists():
        raise FileNotFoundError(f"目录不存在: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"不是目录: {input_dir}")
    dir_pdfs = sorted(
        (p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
        key=lambda p: p.name,
    )
    pdfs.extend(str(p) for p in dir_pdfs)
    return pdfs


def _run_category(
    label: str,
    pdfs: list[str],
    *,
    output_root: Path,
    backup_dest_dir: Path,
    run_date: str,
    results_dir: Path | None,
    results_path: Path,
) -> None:
    if not pdfs:
        return
    print(f"[{label}] 输入数量: {len(pdfs)}")
    run_pipeline(
        pdfs,
        output_root=output_root,
        backup_dest_dir=backup_dest_dir,
        category=label,
        run_date=run_date,
        results_dir=results_dir,
        results_path=results_path,
        dpi=300,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run pipeline for BAR and Beleg in one run and merge into one JSON."
    )
    parser.add_argument("--bar", nargs="*", default=[], help="BAR PDF file paths")
    parser.add_argument("--beleg", nargs="*", default=[], help="Beleg PDF file paths")
    parser.add_argument("--bar-dir", type=Path, help="Directory containing BAR PDFs")
    parser.add_argument("--beleg-dir", type=Path, help="Directory containing Beleg PDFs")
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
        "--run_date",
        dest="run_date",
        default=datetime.now().strftime("%d/%m/%Y"),
        help="Run date in DD/MM/YYYY",
    )
    args = parser.parse_args()

    bar_pdfs = _collect_pdfs(args.bar, args.bar_dir)
    beleg_pdfs = _collect_pdfs(args.beleg, args.beleg_dir)

    if not bar_pdfs and not beleg_pdfs:
        print("必须提供 BAR 或 Beleg 的 PDF（或目录）。")
        raise SystemExit(1)

    output_root = ROOT_DIR / "outputs" / "vlm_pipeline"
    timestamp = int(datetime.now().timestamp())
    results_dir = args.results_dir or output_root
    results_path = results_dir / f"results_{timestamp}.json"

    _run_category(
        "BAR",
        bar_pdfs,
        output_root=output_root,
        backup_dest_dir=args.backup_dest_dir,
        run_date=args.run_date,
        results_dir=results_dir,
        results_path=results_path,
    )
    _run_category(
        "Beleg",
        beleg_pdfs,
        output_root=output_root,
        backup_dest_dir=args.backup_dest_dir,
        run_date=args.run_date,
        results_dir=results_dir,
        results_path=results_path,
    )

    print(f"检测结果已保存: {results_path}")


if __name__ == "__main__":
    main()
