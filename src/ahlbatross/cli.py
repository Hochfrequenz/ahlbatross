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

from ahlbatross.main import DEFAULT_OUTPUT_DIR, process_ahb_data

RELATIVE_PATH_TO_SUBMODULE = Path("data/machine-readable_anwendungshandbuecher")

app = typer.Typer(help="ahlbatross diffs machine-readable AHBs")
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
err_console = Console(stderr=True)  # https://typer.tiangolo.com/tutorial/printing/#printing-to-standard-error


@app.command()
def main(
    input_dir: Optional[Path] = typer.Option(
        None, help="directory containing AHB data, defaults to data/machine-readable_anwendungshandbuecher"
    ),
    output_dir: Optional[Path] = typer.Option(None, help="directory for output files"),
) -> None:
    """
    main entrypoint for AHlBatross.
    """
    try:
        root_dir = input_dir if input_dir else RELATIVE_PATH_TO_SUBMODULE
        if not root_dir.exists():
            _logger.error("❌ input directory does not exist: %s", root_dir.absolute())
            sys.exit(1)
        process_ahb_data(root_dir, output_dir or DEFAULT_OUTPUT_DIR)
    except (OSError, pd.errors.EmptyDataError, ValueError) as e:
        _logger.exception("❌ error processing AHB files")
        sys.exit(1)


def cli() -> None:
    """entry point of the script defined in pyproject.toml"""
    # ⚠ If you ever change the name of this module (cli.py) or this function (def cli), be
    # sure to update pyproject.toml
    app()


# run locally using $ PYTHONPATH=src python -m ahlbatross.cli
if __name__ == "__main__":
    main()
