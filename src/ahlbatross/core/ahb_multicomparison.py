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
from ahlbatross.formats.xlsx import export_to_xlsx

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

        while True:
            selected_fv = Prompt.ask("\nSELECT FV")
            if selected_fv in [str(fv) for fv in formatversions]:
                break
            console.print("❌ Invalid FV.")

        available_pids = get_available_pids(input_dir, selected_fv)
        if not available_pids:
            logger.error("❌ No PIDs found in format version %s", selected_fv)
            sys.exit(1)

        # show available PIDs
        pids_list = ", ".join(available_pids)
        console.print(f"\nAVAILABLE PIDs: {pids_list}")

        while True:
            first_pruefid = Prompt.ask("\nSELECT PID #1")
            if first_pruefid in available_pids:
                break
            console.print("❌ Invalid PID.")

        # show available FVs
        formatversions_list = ", ".join(str(fv) for fv in formatversions)
        console.print(f"\nAVAILABLE FVs: {formatversions_list}")

        while True:
            second_fv = Prompt.ask("\nSELECT FV #2")
            if second_fv in [str(fv) for fv in formatversions]:
                break
            console.print("❌ Invalid format version.")

        second_available_pids = get_available_pids(input_dir, second_fv)
        if not second_available_pids:
            logger.error("❌ No PIDs found for format version %s", second_fv)
            sys.exit(1)

        # show available PIDs
        second_pids_list = ", ".join(second_available_pids)
        console.print(f"\nAVAILABLE PIDs (FV{second_fv}): {second_pids_list}")

        while True:
            second_pruefid = Prompt.ask("\nSELECT PID #2")
            # allow same PIDs only if FVs are different
            if second_pruefid in second_available_pids:
                if second_pruefid == first_pruefid and selected_fv == second_fv:
                    console.print("❌ Cannot compare identical PIDs of the same format version.")
                else:
                    break
            else:
                console.print("❌ Invalid PID.")

        first_file = find_pruefid_file(input_dir, selected_fv, first_pruefid)
        second_file = find_pruefid_file(input_dir, selected_fv, second_pruefid)

        if not first_file or not second_file:
            logger.error("❌ Could not find any <PID>.json files.")
            sys.exit(1)

        first_file_path, first_nf = first_file
        second_file_path, second_nf = second_file

        previous_rows, subsequent_rows = load_csv_files(first_file_path, second_file_path, selected_fv, second_fv)
        comparisons = align_ahb_rows(previous_rows, subsequent_rows)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_basename = f"{first_pruefid}_{second_pruefid}"
        xlsx_path = output_dir / f"{output_basename}.xlsx"

        export_to_xlsx(comparisons, str(xlsx_path))

        logger.info("✅ Successfully merged PIDs")
        logger.info("XLSX output: %s", xlsx_path)

    except Exception as e:
        logger.exception("❌ Error: %s", str(e))
        sys.exit(1)
