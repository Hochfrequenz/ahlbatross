"""
Entrypoint for typer and the command line interface.
"""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

import py7zr
import typer
from rich.console import Console

from ahlbatross.core.ahb_diff import populate_comparison_tables

logger = logging.getLogger(__name__)

app = typer.Typer(help="ahlbatross diffs machine-readable AHBs")
err_console = Console(stderr=True)  # https://typer.tiangolo.com/tutorial/printing/#printing-to-standard-error


@app.command()
def populate_db(
    db_path: Path = typer.Argument(..., help="Path to the SQLite database file or encrypted .7z archive."),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="Password for encrypted .7z archive. If provided, archive is decrypted, processed, re-encrypted.",
        envvar="SQLITE_AHB_DB_7Z_ARCHIVE_PASSWORD",
    ),
) -> None:
    """
    Populate comparison tables in the database for all format version pairs.

    This command creates comparison tables (ahb_line_comparison, ahb_comparison_summary)
    and populates them with comparisons for all Prüfidentifikators across all pairs
    of format versions found in the database.

    If the input is an encrypted .7z archive, provide the password via --password or
    the SQLITE_AHB_DB_7Z_ARCHIVE_PASSWORD environment variable. The archive will be
    decrypted, processed, and re-encrypted with the same password.
    """
    console = Console()

    if not db_path.exists():
        err_console.print(f"[red]Error: File not found: {db_path}[/red]")
        sys.exit(1)

    is_7z_archive = db_path.suffix == ".7z"

    try:
        if is_7z_archive:
            console.print(f"[blue]Extracting {db_path}...[/blue]")
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)

                with py7zr.SevenZipFile(db_path, mode="r", password=password) as archive:
                    archive.extractall(path=tmp_path)

                extracted_db_path = tmp_path / "ahb.db"
                if not extracted_db_path.exists():
                    extracted_files = list(tmp_path.iterdir())
                    if len(extracted_files) == 1:
                        extracted_db_path = extracted_files[0]
                    else:
                        err_console.print(
                            f"[red]Error: Could not find database in archive. Found: {extracted_files}[/red]"
                        )
                        sys.exit(1)

                console.print("[blue]Populating comparison tables...[/blue]")
                total_comparisons = populate_comparison_tables(extracted_db_path)
                console.print(f"[green]Created {total_comparisons} comparisons.[/green]")

                console.print(f"[blue]Re-archiving to {db_path}...[/blue]")
                db_path.unlink()
                with py7zr.SevenZipFile(db_path, mode="w", password=password) as archive:
                    archive.write(extracted_db_path, arcname="ahb.db")

                console.print(f"[green]Successfully updated {db_path}[/green]")
        else:
            console.print(f"[blue]Populating comparison tables in {db_path}...[/blue]")
            total_comparisons = populate_comparison_tables(db_path)
            console.print(f"[green]Successfully created {total_comparisons} comparisons.[/green]")

    except py7zr.Bad7zFile as e:
        err_console.print(f"[red]Error: Invalid or corrupted .7z archive: {e}[/red]")
        sys.exit(1)
    except py7zr.PasswordRequired:
        err_console.print("[red]Error: Password required but not provided or incorrect.[/red]")
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("Error populating comparison tables: %s", str(e))
        err_console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cli() -> None:
    """
    Entry point of the script defined in pyproject.toml
    """
    app()


# to run the script during local development, execute one of the following commands:
# PYTHONPATH=src python -m ahlbatross.main -i data/machine-readable_anwendungshandbuecher -o data/output
# PYTHONPATH=src python -m ahlbatross.main multicompare -i data/machine-readable_anwendungshandbuecher -o data/output
if __name__ == "__main__":
    cli()
