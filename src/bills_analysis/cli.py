from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Set

import typer
from rich.console import Console

from .contracts import ExtractionResult, WarningItem
from .preprocess import detect_pdf_has_text_layer, preprocess_pages
from .render import render_pdf_to_images
from .text_extraction import extract_text_layer_tokens, ocr_tokens_paddle, save_tokens

app = typer.Typer(help="Invoice OCR/extraction CLI (skeleton).")
console = Console()


def _ensure_src_on_path() -> None:
    """Allow running `python cli/main.py` without installation."""
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))


def _write_placeholder(
    out_dir: Path,
    document_name: str,
    debug: bool,
    pages,
    meta_extra: dict | None = None,
    warnings: list[WarningItem] | None = None,
) -> Path:
    """Write a stub extraction.json that follows the contract."""
    result = ExtractionResult(
        document_name=document_name,
        pages=pages,
        fields=[],
        warnings=warnings or [],
        artifacts={},
        meta={
            "status": "skeleton",
            "debug": str(debug),
            **(meta_extra or {}),
        },
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "extraction.json"
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def _iter_pdfs(inputs: Iterable[str]) -> Iterable[Path]:
    """Expand provided paths, directories, or glob patterns into PDF files."""

    seen: Set[Path] = set()
    for raw in inputs:
        path = Path(raw)

        # Glob pattern expansion (e.g., data/samples/**/*.pdf)
        if any(char in raw for char in ["*", "?"]):
            for match in path.parent.glob(path.name):
                if match.is_file() and match.suffix.lower() == ".pdf" and match not in seen:
                    seen.add(match)
                    yield match
            continue

        # Directory expansion
        if path.is_dir():
            for match in path.rglob("*.pdf"):
                if match not in seen:
                    seen.add(match)
                    yield match
            continue

        # Single file (even if it doesn't exist yet, we pass it through)
        if path not in seen:
            seen.add(path)
            yield path


@app.command()
def extract(
    pdf_path: Path,
    out: Path = Path("outputs/run1"),
    dpi: int = typer.Option(200, help="Rendering DPI for page images."),
    preprocess: bool = typer.Option(True, help="Run preprocessing on rendered pages."),
    force_preprocess: bool = typer.Option(
        False, help="Preprocess even if a text layer is detected."
    ),
    debug: bool = False,
) -> None:
    """
    Run the single-file extraction pipeline (skeleton stub).

    The real pipeline will render, preprocess, OCR, extract fields, and emit artifacts
    into `out`. This stub only creates the output folder and a placeholder JSON.
    """

    console.print(f"[cyan]Running skeleton extract for[/cyan] {pdf_path}")
    has_text_layer = detect_pdf_has_text_layer(pdf_path)
    pages = render_pdf_to_images(pdf_path, out / "pages", dpi=dpi)
    pages = preprocess_pages(
        pages,
        output_dir=out / "preproc",
        enable=preprocess and (force_preprocess or not has_text_layer),
    )

    # OCR-first; if quality looks bad and text-layer exists, fallback to text-layer tokens.
    image_paths = [Path(p.preprocessed_path or p.source_path) for p in pages if p.source_path]
    page_numbers = [p.page_no for p in pages if p.source_path]
    tokens, ocr_meta = ocr_tokens_paddle(image_paths, page_numbers, pages)
    tokens_strategy = "ocr"
    fallback_used = False
    warning_items: list[WarningItem] = []
    if has_text_layer and (
        ocr_meta.get("ocr_anomalous") == "true" or ocr_meta.get("ocr_error")
    ):
        text_tokens = extract_text_layer_tokens(pdf_path)
        if text_tokens.tokens:
            tokens = text_tokens
            tokens_strategy = "text-layer"
            fallback_used = True
    elif not has_text_layer and (ocr_meta.get("ocr_error") or not tokens.tokens):
        warning_items.append(
            WarningItem(
                code="OCR_UNAVAILABLE",
                message="OCR failed or unavailable and no text layer present; tokens missing.",
                severity="error",
            )
        )
    tokens_path = save_tokens(tokens, out / "tokens.json")

    placeholder = _write_placeholder(
        out,
        pdf_path.name,
        debug,
        pages=pages,
        meta_extra={
            "renderer": "pymupdf",
            "dpi": str(dpi),
            "has_text_layer": str(has_text_layer),
            "preprocess_enabled": str(preprocess and (force_preprocess or not has_text_layer)),
            "force_preprocess": str(force_preprocess),
            "tokens_strategy": tokens_strategy,
            "tokens_path": str(tokens_path) if tokens_path else "",
            "ocr_fallback_used": str(fallback_used),
            "ocr_lang": ocr_meta.get("ocr_lang", ""),
            "ocr_fallback_lang": ocr_meta.get("ocr_fallback_lang", ""),
            "ocr_error": ocr_meta.get("ocr_error", ""),
        },
        warnings=warning_items,
    )
    console.print(f"[green]Wrote placeholder[/green] {placeholder}")


@app.command()
def batch(
    paths: List[str] = typer.Argument(
        ...,
        help="PDF file(s), directory/directories, or glob patterns (e.g., data/samples/**/*.pdf)",
    ),
    out: Path = Path("outputs/runs"),
    dpi: int = typer.Option(200, help="Rendering DPI for page images."),
    preprocess: bool = typer.Option(True, help="Run preprocessing on rendered pages."),
    force_preprocess: bool = typer.Option(
        False, help="Preprocess even if a text layer is detected."
    ),
    debug: bool = False,
) -> None:
    """
    Batch processing stub. Enumerates PDFs from given inputs and writes placeholders.

    Future work: per-file run folders, diffable outputs, and aggregation.
    """

    out.mkdir(parents=True, exist_ok=True)
    targets = list(_iter_pdfs(paths))
    if not targets:
        console.print("[yellow]No PDFs matched pattern; nothing to do.[/yellow]")
        raise typer.Exit(code=0)

    for pdf in targets:
        run_dir = out / pdf.stem
        has_text_layer = detect_pdf_has_text_layer(pdf)
        pages = render_pdf_to_images(pdf, run_dir / "pages", dpi=dpi)
        pages = preprocess_pages(
            pages,
            output_dir=run_dir / "preproc",
            enable=preprocess and (force_preprocess or not has_text_layer),
        )

        image_paths = [Path(p.preprocessed_path or p.source_path) for p in pages if p.source_path]
        page_numbers = [p.page_no for p in pages if p.source_path]
        tokens, ocr_meta = ocr_tokens_paddle(image_paths, page_numbers, pages)
        tokens_strategy = "ocr"
        fallback_used = False
        warning_items: list[WarningItem] = []
        if has_text_layer and (
            ocr_meta.get("ocr_anomalous") == "true" or ocr_meta.get("ocr_error")
        ):
            text_tokens = extract_text_layer_tokens(pdf)
            if text_tokens.tokens:
                tokens = text_tokens
                tokens_strategy = "text-layer"
                fallback_used = True
        elif not has_text_layer and (ocr_meta.get("ocr_error") or not tokens.tokens):
            warning_items.append(
                WarningItem(
                    code="OCR_UNAVAILABLE",
                    message="OCR failed or unavailable and no text layer present; tokens missing.",
                    severity="error",
                )
            )
        tokens_path = save_tokens(tokens, run_dir / "tokens.json")

        placeholder = _write_placeholder(
            run_dir,
            pdf.name,
            debug,
            pages=pages,
            meta_extra={
                "renderer": "pymupdf",
                "dpi": str(dpi),
                "has_text_layer": str(has_text_layer),
                "preprocess_enabled": str(preprocess and (force_preprocess or not has_text_layer)),
                "force_preprocess": str(force_preprocess),
                "tokens_strategy": tokens_strategy,
                "tokens_path": str(tokens_path) if tokens_path else "",
                "ocr_fallback_used": str(fallback_used),
                "ocr_lang": ocr_meta.get("ocr_lang", ""),
                "ocr_fallback_lang": ocr_meta.get("ocr_fallback_lang", ""),
                "ocr_error": ocr_meta.get("ocr_error", ""),
            },
            warnings=warning_items,
        )
        console.print(f"[green]Prepared[/green] {placeholder}")


def main() -> None:
    _ensure_src_on_path()
    app()


if __name__ == "__main__":
    main()
