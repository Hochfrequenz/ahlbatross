"""
AHB data fetching and parsing as well as csv imports, processing and exports.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Tuple

import pandas as pd
from pandas.core.frame import DataFrame
from xlsxwriter.format import Format  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)

SUBMODULE = Path("data/machine-readable_anwendungshandbuecher")
OUTPUT_DIR = Path("data/output")


def parse_formatversions(formatversion: str) -> Tuple[int, int]:
    """
    parse <formatversion> string (e.g., "FV2504") into year and month.
    """
    if not formatversion.startswith("FV") or len(formatversion) != 6:
        raise ValueError(f"invalid formatversion: {formatversion}")

    year = int(formatversion[2:4])
    month = int(formatversion[4:6])
    year = 2000 + year

    if not 1 <= month <= 12:
        raise ValueError(f"invalid formatversion: {formatversion}")

    return year, month


def get_available_formatversions() -> list[str]:
    """
    get all available <formatversion> directories in SUBMODULE, sorted from latest to oldest.
    """
    if not SUBMODULE.exists():
        logger.error("❌Base directory does not exist: %s", SUBMODULE)
        return []

    formatversion_dirs = [
        d.name for d in SUBMODULE.iterdir() if d.is_dir() and d.name.startswith("FV") and len(d.name) == 6
    ]

    formatversion_dirs.sort(key=parse_formatversions, reverse=True)

    return formatversion_dirs


def is_formatversion_empty(formatversion: str) -> bool:
    """
    check if a <formatversion> directory does not contain any <nachrichtenformat> directories.
    """
    formatversion_dir = SUBMODULE / formatversion
    if not formatversion_dir.exists():
        return True

    return len(get_nachrichtenformat_dirs(formatversion_dir)) == 0


def determine_consecutive_formatversions() -> list[Tuple[str, str]]:
    """
    generate pairs of consecutive <formatversion> directories to compare and skip empty directories.
    """
    formatversion_list = get_available_formatversions()
    consecutive_formatversions = []

    for i in range(len(formatversion_list) - 1):
        subsequent_formatversion = formatversion_list[i]
        previous_formatversion = formatversion_list[i + 1]

        # skip if either directory is empty.
        if is_formatversion_empty(subsequent_formatversion) or is_formatversion_empty(previous_formatversion):
            logger.warning(
                "⚠️skipping empty consecutive formatversions: %s -> %s",
                subsequent_formatversion,
                previous_formatversion,
            )
            continue

        consecutive_formatversions.append((subsequent_formatversion, previous_formatversion))

    return consecutive_formatversions


def get_nachrichtenformat_dirs(formatversion_dir: Path) -> list[Path]:
    """
    get all <nachrichtenformat> directories that contain a csv subdirectory.
    """
    if not formatversion_dir.exists():
        logger.warning("❌formatversion directory not found: %s", formatversion_dir)
        return []

    return [d for d in formatversion_dir.iterdir() if d.is_dir() and (d / "csv").exists() and (d / "csv").is_dir()]


def get_ahb_files(csv_dir: Path) -> list[Path]:
    """
    get all ahb/<pruefid>.csv files in a given directory.
    """
    if not csv_dir.exists():
        return []
    return sorted(csv_dir.glob("*.csv"))


# pylint:disable=too-many-locals
def get_matching_files(previous_formatversion: str, subsequent_formatversion: str) -> list[tuple[Path, Path, str, str]]:
    """
    find matching ahb/<pruefid>.csv files across <formatversion> and <nachrichtenformat> directories.
    """
    previous_formatversion_dir = SUBMODULE / previous_formatversion
    subsequent_formatversion_dir = SUBMODULE / subsequent_formatversion

    if not all(d.exists() for d in [previous_formatversion_dir, subsequent_formatversion_dir]):
        logger.error("❌at least one formatversion directory does not exist.")
        return []

    matching_files = []

    previous_nachrichtenformat_dirs = get_nachrichtenformat_dirs(previous_formatversion_dir)
    subsequent_nachrichtenformat_dirs = get_nachrichtenformat_dirs(subsequent_formatversion_dir)

    previous_nachrichtenformat_names = {d.name: d for d in previous_nachrichtenformat_dirs}
    subsequent_nachrichtenformat_names = {d.name: d for d in subsequent_nachrichtenformat_dirs}

    common_nachrichtentyp = set(previous_nachrichtenformat_names.keys()) & set(
        subsequent_nachrichtenformat_names.keys()
    )

    for nachrichtentyp in sorted(common_nachrichtentyp):
        previous_csv_dir = previous_nachrichtenformat_names[nachrichtentyp] / "csv"
        subsequent_csv_dir = subsequent_nachrichtenformat_names[nachrichtentyp] / "csv"

        previous_files = {f.stem: f for f in get_ahb_files(previous_csv_dir)}
        subsequent_files = {f.stem: f for f in get_ahb_files(subsequent_csv_dir)}

        common_ahbs = set(previous_files.keys()) & set(subsequent_files.keys())

        for pruefid in sorted(common_ahbs):
            matching_files.append((previous_files[pruefid], subsequent_files[pruefid], nachrichtentyp, pruefid))

    return matching_files


def get_csv(previous_ahb_path: Path, subsequent_ahb_path: Path) -> tuple[DataFrame, DataFrame]:
    """
    read csv input files.
    """
    previous_ahb: DataFrame = pd.read_csv(previous_ahb_path, dtype=str)
    subsequent_ahb: DataFrame = pd.read_csv(subsequent_ahb_path, dtype=str)
    return previous_ahb, subsequent_ahb


def create_row(
    previous_df: DataFrame | None = None, new_df: DataFrame | None = None, i: int | None = None, j: int | None = None
) -> dict[str, Any]:
    """
    fills rows for all columns that belong to one dataframe depending on whether old/new segments already exist.
    """
    row = {"Segmentname_old": "", "diff": "", "Segmentname_new": ""}

    if previous_df is not None:
        for col in previous_df.columns:
            if col != "Segmentname_old":
                row[f"{col}_old"] = ""

    if new_df is not None:
        for col in new_df.columns:
            if col != "Segmentname_new":
                row[f"{col}_new"] = ""

    if previous_df is not None and i is not None:
        row["Segmentname_old"] = previous_df.iloc[i]["Segmentname_old"]
        for col in previous_df.columns:
            if col != "Segmentname_old":
                value = previous_df.iloc[i][col]
                row[f"{col}_old"] = "" if pd.isna(value) else value

    if new_df is not None and j is not None:
        row["Segmentname_new"] = new_df.iloc[j]["Segmentname_new"]
        for col in new_df.columns:
            if col != "Segmentname_new":
                value = new_df.iloc[j][col]
                row[f"{col}_new"] = "" if pd.isna(value) else value

    return row


# pylint:disable=too-many-statements
def align_columns(previous_pruefid: DataFrame, subsequent_pruefid: DataFrame) -> DataFrame:
    """
    aligns `Segmentname` columns by adding empty cells each time the cell values do not match.
    """
    # add suffixes to columns.
    df_old = previous_pruefid.copy()
    df_new = subsequent_pruefid.copy()
    df_old = df_old.rename(columns={"Segmentname": "Segmentname_old"})
    df_new = df_new.rename(columns={"Segmentname": "Segmentname_new"})

    # preserve column order.
    old_columns = [col for col in previous_pruefid.columns if col != "Segmentname"]
    new_columns = [col for col in subsequent_pruefid.columns if col != "Segmentname"]

    column_order = (
        ["Segmentname_old"]
        + [f"{col}_old" for col in old_columns]
        + ["diff"]
        + ["Segmentname_new"]
        + [f"{col}_new" for col in new_columns]
    )

    if df_old.empty and df_new.empty:
        return pd.DataFrame({col: pd.Series([], dtype="float64") for col in column_order})

    if df_new.empty:
        result_rows = [create_row(previous_df=df_old, new_df=df_new, i=i) for i in range(len(df_old))]
        for row in result_rows:
            row["diff"] = "REMOVED"
        result_df = pd.DataFrame(result_rows)
        return result_df[column_order]

    if df_old.empty:
        result_rows = [create_row(previous_df=df_old, new_df=df_new, j=j) for j in range(len(df_new))]
        for row in result_rows:
            row["diff"] = "NEW"
        result_df = pd.DataFrame(result_rows)
        return result_df[column_order]

    segments_old = df_old["Segmentname_old"].tolist()
    segments_new = df_new["Segmentname_new"].tolist()
    result_rows = []

    i = 0
    j = 0

    # iterate through both lists until reaching their ends.
    while i < len(segments_old) or j < len(segments_new):
        if i >= len(segments_old):
            row = create_row(previous_df=df_old, new_df=df_new, j=j)
            row["diff"] = "NEW"
            result_rows.append(row)
            j += 1
        elif j >= len(segments_new):
            row = create_row(previous_df=df_old, new_df=df_new, i=i)
            row["diff"] = "REMOVED"
            result_rows.append(row)
            i += 1
        elif segments_old[i] == segments_new[j]:
            row = create_row(previous_df=df_old, new_df=df_new, i=i, j=j)
            row["diff"] = ""
            result_rows.append(row)
            i += 1
            j += 1
        else:
            # try to find next matching value.
            try:
                next_match_new = segments_new[j:].index(segments_old[i])
                for _ in range(next_match_new):
                    row = create_row(previous_df=df_old, new_df=df_new, j=j)
                    row["diff"] = "NEW"
                    result_rows.append(row)
                    j += 1
                continue
            except ValueError:
                # no match found: add old value and empty new cell.
                row = create_row(previous_df=df_old, new_df=df_new, i=i)
                row["diff"] = "REMOVED"  # Segment only in old file
                result_rows.append(row)
                i += 1

    # create dataframe with string dtype and replace NaN with empty strings.
    result_df = pd.DataFrame(result_rows).astype(str).replace("nan", "")
    return result_df[column_order]


# pylint:disable=too-many-locals
def export_to_excel(df: DataFrame, output_path_xlsx: str) -> None:
    """
    exports the merged dataframe to .xlsx with highlighted differences.
    """
    df_filtered = df[[col for col in df.columns if not col.startswith("Unnamed:")]]

    with pd.ExcelWriter(output_path_xlsx, engine="xlsxwriter") as writer:
        df_filtered.to_excel(writer, sheet_name="AHB-Diff", index=False)

        workbook = writer.book
        worksheet = writer.sheets["AHB-Diff"]

        # base formatting
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D9D9D9", "border": 1, "align": "center", "text_wrap": True}
        )
        base_format = workbook.add_format({"border": 1, "text_wrap": True})

        # formatting highlighted/changed cells
        diff_formats: dict[str, Format] = {
            "NEW": workbook.add_format({"bg_color": "#C6EFCE", "border": 1, "text_wrap": True}),
            "REMOVED": workbook.add_format({"bg_color": "#FFC7CE", "border": 1, "text_wrap": True}),
            "": workbook.add_format({"border": 1, "text_wrap": True}),
        }

        # formatting diff column.
        diff_text_formats: dict[str, Format] = {
            "NEW": workbook.add_format(
                {
                    "bold": True,
                    "color": "#7AAB8A",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "REMOVED": workbook.add_format(
                {
                    "bold": True,
                    "color": "#E94C74",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "": workbook.add_format({"border": 1, "bg_color": "#D9D9D9", "align": "center", "text_wrap": True}),
        }

        for col_num, value in enumerate(df_filtered.columns.values):
            worksheet.write(0, col_num, value, header_format)

        diff_idx = df_filtered.columns.get_loc("diff")

        def _try_convert_to_number(cell: str) -> int | float | str:
            """
            tries to format cell values to numbers where appropriate.
            """
            try:
                if cell.isdigit():
                    return int(cell)
                return float(cell)
            except ValueError:
                return cell

        for row_num, row in enumerate(df_filtered.itertuples(index=False), start=1):
            row_data = list(row)
            diff_value = str(row_data[diff_idx])

            for col_num, (value, col_name) in enumerate(zip(row_data, df_filtered.columns)):
                converted_value = _try_convert_to_number(str(value)) if value != "" else ""

                if col_name == "diff":
                    worksheet.write(row_num, col_num, value, diff_text_formats[diff_value])
                elif diff_value == "REMOVED" and col_name.endswith("_old"):
                    worksheet.write(row_num, col_num, converted_value, diff_formats["REMOVED"])
                elif diff_value == "NEW" and col_name.endswith("_new"):
                    worksheet.write(row_num, col_num, converted_value, diff_formats["NEW"])
                else:
                    worksheet.write(row_num, col_num, converted_value, base_format)

        for col_num in range(len(df_filtered.columns)):
            worksheet.set_column(col_num, col_num, min(150 / 7, 21))  # cell width = 150 px.

        logger.info("✅successfully exported XLSX file to: %s", {output_path_xlsx})


def process_files(previous_formatversion: str, subsequent_formatversion: str) -> None:
    """
    process all matching ahb/<pruefid>.csv files between two <formatversion> directories.
    """
    matching_files = get_matching_files(previous_formatversion, subsequent_formatversion)

    if not matching_files:
        logger.warning("No matching files found to compare")
        return

    output_base = OUTPUT_DIR / f"{subsequent_formatversion}_{previous_formatversion}"

    for old_file, new_file, nachrichtentyp, pruefid in matching_files:
        logger.info("Processing %s - %s", nachrichtentyp, pruefid)

        try:
            df_old, df_new = get_csv(old_file, new_file)
            merged_df = align_columns(df_old, df_new)

            output_dir = output_base / nachrichtentyp
            output_dir.mkdir(parents=True, exist_ok=True)

            csv_path = output_dir / f"{pruefid}.csv"
            xlsx_path = output_dir / f"{pruefid}.xlsx"

            merged_df.to_csv(csv_path, index=False)
            export_to_excel(merged_df, str(xlsx_path))

            logger.info("✅successfully processed %s/%s", nachrichtentyp, pruefid)

        except pd.errors.EmptyDataError:
            logger.error("❌empty or corrupted CSV file for %s/%s", nachrichtentyp, pruefid)
        except OSError as e:
            logger.error("❌file system error for %s/%s: %s", nachrichtentyp, pruefid, str(e))
        except ValueError as e:
            logger.error("❌data processing error for %s/%s: %s", nachrichtentyp, pruefid, str(e))


def process_submodule() -> None:
    """
    processes all valid consecutive <formatversion> subdirectories.
    """
    consecutive_formatversions = determine_consecutive_formatversions()

    if not consecutive_formatversions:
        logger.warning("⚠️no valid consecutive formatversion subdirectories found to compare")
        return

    for subsequent_formatversion, previous_formatversion in consecutive_formatversions:
        logger.info(
            "⌛processing consecutive formatversions: %s -> %s", subsequent_formatversion, previous_formatversion
        )
        try:
            process_files(previous_formatversion, subsequent_formatversion)
        except (OSError, pd.errors.EmptyDataError, ValueError) as e:
            logger.error(
                "❌error processing formatversions %s -> %s: %s",
                subsequent_formatversion,
                previous_formatversion,
                str(e),
            )
            continue


if __name__ == "__main__":
    process_submodule()
