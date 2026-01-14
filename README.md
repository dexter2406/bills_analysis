# bills_analysis

Local backend CLI skeleton for the invoice Azure API extraction PoC.

## Run style
- Preferred: `uv run invoice --help` (uses `pyproject.toml` deps).
- Alt: `python cli/main.py --help` for editable runs without install.

### Python version
- Project targets Python 3.10–3.11.

## Dependencies
- PyMuPDF for PDF rendering; Pillow for preprocessing.
- Azure Document Intelligence for extraction (`azure-ai-documentintelligence`).
- Configure `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` and `AZURE_DOCUMENT_INTELLIGENCE_KEY` in `.env`.

## Layout
- `src/bills_analysis/`: core package and `contracts.py` for `extraction.json`.
- `cli/main.py`: local entrypoint that forwards to the Typer app.
- `tests/`: minimal CLI regression placeholder.
- `data/samples/`: drop electronic and scanned PDF fixtures here.
- `outputs/`: runtime artifacts; see `outputs/extraction.example.json` for the contract.

## Usage examples
- Azure API pipeline (PDFs can be multi-page):  
  `uv run python tests/vlm_pipeline_api.py data/samples/digitized/demo.pdf --dest-dir=outputs/comp_pdf`

## Next steps (per PoC)
- Fill the pipeline (render → preprocess → Azure API → extract → evidence) inside `src/bills_analysis/`.
- Add golden sample PDFs and expected outputs under `data/samples/` and `tests/`.
