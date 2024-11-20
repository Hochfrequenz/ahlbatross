"""
entrypoint for typer and the command line interface (CLI)
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console

from ahlbatross.main import process_ahb_data

app = typer.Typer(help="ahlbatross diffs machine-readable AHBs")
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
err_console = Console(stderr=True)  # https://typer.tiangolo.com/tutorial/printing/#printing-to-standard-error


@app.command()
def main(
    input_dir: Path = typer.Option(..., "--input-dir", "-i", help="Directory containing AHB data."),
    output_dir: Path = typer.Option(
        ..., "--output-dir", "-o", help="Destination path to output directory containing processed files."
    ),
) -> None:
    """
    main entrypoint for AHlBatross.
    """
    try:
        if not input_dir.exists():
            _logger.error("❌ Input directory does not exist: %s", input_dir.absolute())
            sys.exit(1)
        process_ahb_data(input_dir, output_dir)
    except (OSError, pd.errors.EmptyDataError, ValueError) as _:
        _logger.exception("❌ Error processing AHB files.")
        sys.exit(1)


def cli() -> None:
    """entry point of the script defined in pyproject.toml"""
    # ⚠ If you ever change the name of this module (cli.py) or this function (def cli), be
    # sure to update pyproject.toml
    app()


# to run the script during local development, execute the following command:
# PYTHONPATH=src python -m ahlbatross.cli -i data/machine-readable-anwendungshandbuecher -o data/output
if __name__ == "__main__":
    main()
