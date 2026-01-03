from pathlib import Path

import fitz  # PyMuPDF
from typer.testing import CliRunner

from bills_analysis import cli

runner = CliRunner()


def _make_simple_pdf(path: Path) -> None:
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "Hello Invoice")
        doc.save(path)


def test_extract_writes_placeholder_and_renders(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _make_simple_pdf(pdf_path)
    out_dir = tmp_path / "run"

    result = runner.invoke(
        cli.app,
        [
            "extract",
            str(pdf_path),
            "--out",
            str(out_dir),
            "--dpi",
            "100",
            "--preprocess",
            "--force-preprocess",
        ],
    )

    assert result.exit_code == 0
    extraction = out_dir / "extraction.json"
    assert extraction.exists()
    content = extraction.read_text(encoding="utf-8")
    assert pdf_path.name in content
    pages_dir = out_dir / "pages"
    assert pages_dir.exists()
    assert any(pages_dir.glob("page_*.png"))
    preproc_dir = out_dir / "preproc"
    assert preproc_dir.exists()
    assert any(preproc_dir.glob("page_*.preproc.png"))
    tokens_path = out_dir / "tokens.json"
    assert tokens_path.exists()
