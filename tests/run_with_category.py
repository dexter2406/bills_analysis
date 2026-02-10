from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from bills_analysis.services.process_service import ROOT_DIR, collect_pdfs, run_pipeline_by_category


def main() -> None:
    """CLI wrapper for category-based pipeline execution via src service layer."""

    parser = argparse.ArgumentParser(
        description="Run pipeline for BAR and ZBon in one run and merge into one JSON."
    )
    parser.add_argument("--bar", nargs="*", default=[], help="BAR PDF file paths")
    parser.add_argument("--zbon", nargs="*", default=[], help="ZBon PDF file paths")
    parser.add_argument("--office", nargs="*", default=[], help="OFFICE PDF file paths")
    parser.add_argument("--bar-dir", type=Path, help="Directory containing BAR PDFs")
    parser.add_argument("--zbon-dir", type=Path, help="Directory containing ZBon PDFs")
    parser.add_argument("--office-dir", type=Path, help="Directory containing OFFICE PDFs")
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

    bar_pdfs = collect_pdfs(args.bar, args.bar_dir)
    zbon_pdfs = collect_pdfs(args.zbon, args.zbon_dir)
    office_pdfs = collect_pdfs(args.office, args.office_dir)

    results_path = run_pipeline_by_category(
        bar_pdfs=bar_pdfs,
        zbon_pdfs=zbon_pdfs,
        office_pdfs=office_pdfs,
        backup_dest_dir=args.backup_dest_dir,
        run_date=args.run_date,
        results_dir=args.results_dir,
    )
    print(f"检测结果已保存: {results_path}")


if __name__ == "__main__":
    main()
