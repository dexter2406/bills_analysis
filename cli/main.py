"""Local entrypoint for running the Typer CLI without installing the package."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from bills_analysis.cli import main


if __name__ == "__main__":
    main()
