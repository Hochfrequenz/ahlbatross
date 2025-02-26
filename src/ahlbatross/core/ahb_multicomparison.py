"""
Interactive CLI PID comparison.
Output = xlsx only.
Multiple comparisons PID_A <-> PID_B, PID_A <-> PID_C, PID_A <-> PID_D, ... are merged in separate tabs.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.prompt import Prompt

from ahlbatross.core.ahb_comparison import align_ahb_rows
from ahlbatross.core.ahb_processing import _get_formatversion_dirs, _get_nachrichtenformat_dirs
from ahlbatross.formats.csv import get_csv_files, load_csv_files
from ahlbatross.formats.xlsx import export_to_xlsx_multicompare

logger = logging.getLogger(__name__)
console = Console()


def find_pruefid_file(root_dir: Path, formatversion: str, pruefid: str) -> Optional[Tuple[Path, str]]:
    """
    Find a PID file across all "Nachrichtenformat" directories in a given FV.
    """
    formatversion_dir = root_dir / formatversion
    if not formatversion_dir.exists():
        return None

    nachrichtenformat_dirs = _get_nachrichtenformat_dirs(formatversion_dir)

    for nf_dir in nachrichtenformat_dirs:
        csv_dir = nf_dir / "csv"
        if not csv_dir.exists():
            continue

        for file in get_csv_files(csv_dir):
            if file.stem == pruefid:
                return file, nf_dir.name

    return None


def get_available_pids(root_dir: Path, formatversion: str) -> List[str]:
    """
    Get all available PIDs across all nachrichtenformat directories in a given FV.
    """
    pids = set()
    formatversion_dir = root_dir / formatversion

    if not formatversion_dir.exists():
        return []

    nachrichtenformat_dirs = _get_nachrichtenformat_dirs(formatversion_dir)

    for nf_dir in nachrichtenformat_dirs:
        csv_dir = nf_dir / "csv"
        if not csv_dir.exists():
            continue

        for file in get_csv_files(csv_dir):
            pids.add(file.stem)

    return sorted(list(pids))


# pylint:disable=too-many-locals, too-many-branches, too-many-statements
def multicompare_command(
    input_dir: Path = typer.Option(..., "--input-dir", "-i", help="Directory containing AHB <PID>.json files."),
    output_dir: Path = typer.Option(
        ..., "--output-dir", "-o", help="Destination path to output directory containing merged xlsx files."
    ),
) -> None:
    """
    Interactive command to compare two PIDs across different FVs.
    """
    try:
        if not input_dir.exists():
            logger.error("❌ Input directory does not exist: %s", input_dir.absolute())
            sys.exit(1)

        formatversions = _get_formatversion_dirs(input_dir)
        if not formatversions:
            logger.error("❌ No format versions found in input directory")
            sys.exit(1)

        # show available FVs
        formatversions_list = ", ".join(str(fv) for fv in formatversions)
        console.print(f"\nAVAILABLE FVs: {formatversions_list}")

        # get first FV
        while True:
            first_fv = Prompt.ask("\nSELECT FV")
            if first_fv in [str(fv) for fv in formatversions]:
                break
            console.print("❌ Invalid FV.")

        # get first PID
        first_available_pids = get_available_pids(input_dir, first_fv)
        if not first_available_pids:
            logger.error("❌ No PIDs found in format version %s", first_fv)
            sys.exit(1)

        # show available PIDs
        first_pids_list = ", ".join(first_available_pids)
        console.print(f"\nAVAILABLE PIDs: {first_pids_list}")

        while True:
            first_pruefid = Prompt.ask("\nSELECT PID #1")
            if first_pruefid in first_available_pids:
                break
            console.print("❌ Invalid PID.")

        first_file = find_pruefid_file(input_dir, first_fv, first_pruefid)
        if not first_file:
            logger.error("❌ Could not find PID file for %s in %s", first_pruefid, first_fv)
            sys.exit(1)

        first_file_path, _ = first_file

        comparison_groups = []
        comparison_names = []

        comparison_number = 2
        while True:
            # show available FVs
            formatversions_list = ", ".join(str(fv) for fv in formatversions)
            console.print(f"\nAVAILABLE FVs (🏁 PRESS ENTER TO FINISH): {formatversions_list}")

            next_fv = Prompt.ask(f"\nSELECT FV #{comparison_number}", default="")
            if not next_fv:
                # hitting enter aborts the process.
                break

            if next_fv not in [str(fv) for fv in formatversions]:
                console.print("❌ Invalid FV.")
                continue

            next_available_pids = get_available_pids(input_dir, next_fv)
            if not next_available_pids:
                logger.error("❌ No PIDs found for format version %s", next_fv)
                continue

            # show available PIDs
            next_pids_list = ", ".join(next_available_pids)
            console.print(f"\nAVAILABLE PIDs (FV{next_fv}): {next_pids_list}")

            while True:
                next_pruefid = Prompt.ask(f"\nSELECT PID #{comparison_number}")
                if next_pruefid == first_pruefid and next_fv == first_fv:
                    console.print("❌ Cannot compare identical PIDs of the same format version.")
                elif next_pruefid in next_available_pids:
                    break
                else:
                    console.print("❌ Invalid PID.")

            next_file = find_pruefid_file(input_dir, next_fv, next_pruefid)
            if not next_file:
                logger.error("❌ Could not find PID file for %s in %s", next_pruefid, next_fv)
                continue

            next_file_path, _ = next_file

            try:
                first_rows, next_rows = load_csv_files(first_file_path, next_file_path, first_fv, next_fv)
                comparisons = align_ahb_rows(first_rows, next_rows)

                comparison_groups.append(comparisons)
                comparison_names.append(f"{first_pruefid}_{next_pruefid}")

                comparison_number += 1
            except (OSError, IOError, ValueError) as e:
                logger.error(
                    "❌ Error comparing %s/%s with %s/%s: %s", first_fv, first_pruefid, next_fv, next_pruefid, str(e)
                )
                continue

        if not comparison_groups:
            sys.exit(1)

        output_dir.mkdir(parents=True, exist_ok=True)

        xlsx_path = output_dir / f"{first_pruefid}_comparisons.xlsx"
        export_to_xlsx_multicompare(comparison_groups, comparison_names, str(xlsx_path))

        logger.info("✅ Successfully processed: %s", xlsx_path)

    except (OSError, IOError, ValueError, TypeError) as e:
        logger.exception("❌ Error: %s", str(e))
        sys.exit(1)
