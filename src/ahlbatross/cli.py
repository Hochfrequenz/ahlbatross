"""
entrypoint for typer and the command line interface (CLI)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich.console import Console

from ahlbatross.main import DEFAULT_OUTPUT_DIR, _process_submodule

app = typer.Typer(help="ahlbatross diffs machine-readable AHBs")
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
err_console = Console(stderr=True)  # https://typer.tiangolo.com/tutorial/printing/#printing-to-standard-error


@app.command()
def main(output_dir: Optional[Path] = None) -> None:
    """
    main entrypoint for AHlBatross.
    """
    try:
        _process_submodule(output_dir or DEFAULT_OUTPUT_DIR)
    except (OSError, pd.errors.EmptyDataError, ValueError) as e:
        _logger.error("❌error processing AHB files: %s", str(e))
        sys.exit(1)


def cli() -> None:
    """entry point of the script defined in pyproject.toml"""
    # ⚠ If you ever change the name of this module (cli.py) or this function (def cli), be
    # sure to update pyproject.toml
    app()


# run locally using $ PYTHONPATH=src python -m ahlbatross.cli
if __name__ == "__main__":
    main()
