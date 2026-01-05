from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Set

import typer
from rich.console import Console

from .contracts import ExtractionResult, FieldCandidate, WarningItem
from .preprocess import detect_pdf_has_text_layer, preprocess_pages
from .render import render_pdf_to_images
from .vlm import DEFAULT_PROMPT, infer_invoice_with_ollama

app = typer.Typer(help="Invoice VLM extraction CLI (skeleton).")
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
    model: str = typer.Option("qwen3-vl:4b", help="Ollama model to query."),
    base_url: str = typer.Option("http://localhost:11434", help="Ollama base URL."),
    temperature: float = typer.Option(0.0, help="Sampling temperature for the VLM."),
    prompt: str = typer.Option(
        DEFAULT_PROMPT,
        help="Prompt sent to the VLM. Keep concise; must instruct JSON output.",
        rich_help_panel="Advanced",
    ),
    debug: bool = False,
) -> None:
    """
    Run the single-file extraction pipeline (skeleton stub).

    The real pipeline will render, preprocess, query a VLM, extract fields, and emit artifacts
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

    fields, vlm_meta = infer_invoice_with_ollama(
        pages,
        prompt=prompt,
        model=model,
        base_url=base_url,
        temperature=temperature,
    )

    warning_items: list[WarningItem] = []
    if vlm_meta.get("vlm_error"):
        warning_items.append(
            WarningItem(
                code="VLM_ERROR",
                message=f"Vision model call failed: {vlm_meta['vlm_error']}",
                severity="error",
            )
        )

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
            "vlm_model": vlm_meta.get("vlm_model", ""),
            "vlm_base_url": vlm_meta.get("vlm_base_url", ""),
            "vlm_error": vlm_meta.get("vlm_error", ""),
        },
        warnings=warning_items,
    )
    if fields:
        placeholder_data = ExtractionResult.model_validate_json(
            placeholder.read_text(encoding="utf-8")
        )
        placeholder_data.fields = fields
        placeholder.write_text(placeholder_data.model_dump_json(indent=2), encoding="utf-8")
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
    model: str = typer.Option("qwen3-vl:4b", help="Ollama model to query."),
    base_url: str = typer.Option("http://localhost:11434", help="Ollama base URL."),
    temperature: float = typer.Option(0.0, help="Sampling temperature for the VLM."),
    prompt: str = typer.Option(
        DEFAULT_PROMPT,
        help="Prompt sent to the VLM. Keep concise; must instruct JSON output.",
        rich_help_panel="Advanced",
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

        fields, vlm_meta = infer_invoice_with_ollama(
            pages,
            prompt=prompt,
            model=model,
            base_url=base_url,
            temperature=temperature,
        )

        warning_items: list[WarningItem] = []
        if vlm_meta.get("vlm_error"):
            warning_items.append(
                WarningItem(
                    code="VLM_ERROR",
                    message=f"Vision model call failed: {vlm_meta['vlm_error']}",
                    severity="error",
                )
            )

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
                "vlm_model": vlm_meta.get("vlm_model", ""),
                "vlm_base_url": vlm_meta.get("vlm_base_url", ""),
                "vlm_error": vlm_meta.get("vlm_error", ""),
            },
            warnings=warning_items,
        )
        if fields:
            placeholder_data = ExtractionResult.model_validate_json(
                placeholder.read_text(encoding="utf-8")
            )
            placeholder_data.fields = fields
            placeholder.write_text(placeholder_data.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[green]Prepared[/green] {placeholder}")


def main() -> None:
    _ensure_src_on_path()
    app()


if __name__ == "__main__":
    main()
