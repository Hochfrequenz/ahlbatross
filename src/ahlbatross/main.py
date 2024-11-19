"""
AHB data fetching and parsing as well as csv imports, processing and exports.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Tuple, TypeAlias

import pandas as pd
from pandas.core.frame import DataFrame
from xlsxwriter.format import Format  # type:ignore[import-untyped]

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)

SUBMODULE = Path("data/machine-readable_anwendungshandbuecher")
DEFAULT_OUTPUT_DIR = Path("data/output")

XlsxFormat: TypeAlias = Format


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


def _get_available_formatversions() -> list[str]:
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


def _get_nachrichtenformat_dirs(formatversion_dir: Path) -> list[Path]:
    """
    get all <nachrichtenformat> directories that contain a csv subdirectory.
    """
    if not formatversion_dir.exists():
        logger.warning("❌formatversion directory not found: %s", formatversion_dir)
        return []

    return [d for d in formatversion_dir.iterdir() if d.is_dir() and (d / "csv").exists() and (d / "csv").is_dir()]


def _is_formatversion_dir_empty(formatversion: str) -> bool:
    """
    check if a <formatversion> directory does not contain any <nachrichtenformat> directories.
    """
    formatversion_dir = SUBMODULE / formatversion
    if not formatversion_dir.exists():
        return True

    return len(_get_nachrichtenformat_dirs(formatversion_dir)) == 0


def determine_consecutive_formatversions() -> list[Tuple[str, str]]:
    """
    generate pairs of consecutive <formatversion> directories to compare and skip empty directories.
    """
    formatversion_list = _get_available_formatversions()
    consecutive_formatversions = []

    for i in range(len(formatversion_list) - 1):
        subsequent_formatversion = formatversion_list[i]
        previous_formatversion = formatversion_list[i + 1]

        # skip if either directory is empty.
        if _is_formatversion_dir_empty(subsequent_formatversion) or _is_formatversion_dir_empty(previous_formatversion):
            logger.warning(
                "⚠️skipping empty consecutive formatversions: %s -> %s",
                subsequent_formatversion,
                previous_formatversion,
            )
            continue

        consecutive_formatversions.append((subsequent_formatversion, previous_formatversion))

    return consecutive_formatversions


def _get_pruefid_files(csv_dir: Path) -> list[Path]:
    """
    get all ahb/<pruefid>.csv files in a given directory.
    """
    if not csv_dir.exists():
        return []
    return sorted(csv_dir.glob("*.csv"))


# pylint:disable=too-many-locals
def get_matching_pruefid_files(
    previous_formatversion: str, subsequent_formatversion: str
) -> list[tuple[Path, Path, str, str]]:
    """
    find matching ahb/<pruefid>.csv files across <formatversion> and <nachrichtenformat> directories.
    """
    previous_formatversion_dir = SUBMODULE / previous_formatversion
    subsequent_formatversion_dir = SUBMODULE / subsequent_formatversion

    if not all(d.exists() for d in [previous_formatversion_dir, subsequent_formatversion_dir]):
        logger.error("❌at least one formatversion directory does not exist.")
        return []

    matching_files = []

    previous_nachrichtenformat_dirs = _get_nachrichtenformat_dirs(previous_formatversion_dir)
    subsequent_nachrichtenformat_dirs = _get_nachrichtenformat_dirs(subsequent_formatversion_dir)

    previous_nachrichtenformat_names = {d.name: d for d in previous_nachrichtenformat_dirs}
    subsequent_nachrichtenformat_names = {d.name: d for d in subsequent_nachrichtenformat_dirs}

    common_nachrichtentyp = set(previous_nachrichtenformat_names.keys()) & set(
        subsequent_nachrichtenformat_names.keys()
    )

    for nachrichtentyp in sorted(common_nachrichtentyp):
        previous_csv_dir = previous_nachrichtenformat_names[nachrichtentyp] / "csv"
        subsequent_csv_dir = subsequent_nachrichtenformat_names[nachrichtentyp] / "csv"

        previous_files = {f.stem: f for f in _get_pruefid_files(previous_csv_dir)}
        subsequent_files = {f.stem: f for f in _get_pruefid_files(subsequent_csv_dir)}

        common_ahbs = set(previous_files.keys()) & set(subsequent_files.keys())

        for pruefid in sorted(common_ahbs):
            matching_files.append((previous_files[pruefid], subsequent_files[pruefid], nachrichtentyp, pruefid))

    return matching_files


def _get_csv_content(previous_ahb_path: Path, subsequent_ahb_path: Path) -> tuple[DataFrame, DataFrame]:
    """
    read csv input files.
    """
    previous_ahb: DataFrame = pd.read_csv(previous_ahb_path, dtype=str)
    subsequent_ahb: DataFrame = pd.read_csv(subsequent_ahb_path, dtype=str)
    return previous_ahb, subsequent_ahb


def _populate_row_values(
    df: DataFrame | None,
    row: dict[str, Any],
    idx: int | None,
    formatversion: str,
    is_segmentname: bool = True,
) -> None:
    """
    utility function to populate row values for a given dataframe segment.
    """
    if df is not None and idx is not None:
        segmentname_col = f"Segmentname_{formatversion}"
        if is_segmentname:
            row[segmentname_col] = df.iloc[idx][segmentname_col]
        else:
            for col in df.columns:
                if col != segmentname_col:
                    value = df.iloc[idx][col]
                    row[f"{col}_{formatversion}"] = "" if pd.isna(value) else value


# pylint: disable=too-many-arguments, too-many-positional-arguments
def create_row(
    previous_df: DataFrame | None = None,
    subsequent_df: DataFrame | None = None,
    i: int | None = None,
    j: int | None = None,
    previous_formatversion: str = "",
    subsequent_formatversion: str = "",
) -> dict[str, Any]:
    """
    fills rows for all columns that belong to one dataframe depending on whether previous/subsequent segments exist.
    """
    row = {f"Segmentname_{previous_formatversion}": "", "Änderung": "", f"Segmentname_{subsequent_formatversion}": ""}

    if previous_df is not None:
        for col in previous_df.columns:
            if col != f"Segmentname_{previous_formatversion}":
                row[f"{col}_{previous_formatversion}"] = ""

    if subsequent_df is not None:
        for col in subsequent_df.columns:
            if col != f"Segmentname_{subsequent_formatversion}":
                row[f"{col}_{subsequent_formatversion}"] = ""

    _populate_row_values(previous_df, row, i, previous_formatversion, is_segmentname=True)
    _populate_row_values(subsequent_df, row, j, subsequent_formatversion, is_segmentname=True)

    _populate_row_values(previous_df, row, i, previous_formatversion, is_segmentname=False)
    _populate_row_values(subsequent_df, row, j, subsequent_formatversion, is_segmentname=False)

    return row


# pylint:disable=too-many-branches, too-many-statements
def align_columns(
    previous_pruefid: DataFrame,
    subsequent_pruefid: DataFrame,
    previous_formatversion: str,
    subsequent_formatversion: str,
) -> DataFrame:
    """
    aligns `Segmentname` columns by adding empty cells each time the cell values do not match.
    """

    default_column_order = [
        "Segmentname",
        "Segmentgruppe",
        "Segment",
        "Datenelement",
        "Segment ID",
        "Code",
        "Qualifier",
        "Beschreibung",
        "Bedingungsausdruck",
        "Bedingung",
    ]

    # get all unique columns from both dataframes.
    all_columns = set(previous_pruefid.columns) | set(subsequent_pruefid.columns)

    columns_without_segmentname = []
    for col in default_column_order:
        if col in all_columns and col != "Segmentname":
            columns_without_segmentname.append(col)

    for col in sorted(all_columns):
        if col not in default_column_order and col != "Segmentname":
            columns_without_segmentname.append(col)

    for col in all_columns:
        if col not in previous_pruefid.columns:
            previous_pruefid[col] = ""
        if col not in subsequent_pruefid.columns:
            subsequent_pruefid[col] = ""

    # add corresponding formatversions as suffixes to columns.
    df_of_previous_formatversion = previous_pruefid.copy()
    df_of_subsequent_formatversion = subsequent_pruefid.copy()

    df_of_previous_formatversion = df_of_previous_formatversion.rename(
        columns={"Segmentname": f"Segmentname_{previous_formatversion}"}
    )
    df_of_subsequent_formatversion = df_of_subsequent_formatversion.rename(
        columns={"Segmentname": f"Segmentname_{subsequent_formatversion}"}
    )

    column_order = (
        [f"Segmentname_{previous_formatversion}"]
        + [f"{col}_{previous_formatversion}" for col in columns_without_segmentname]
        + ["Änderung"]
        + ["changed_entries"]
        + [f"Segmentname_{subsequent_formatversion}"]
        + [f"{col}_{subsequent_formatversion}" for col in columns_without_segmentname]
    )

    if df_of_previous_formatversion.empty and df_of_subsequent_formatversion.empty:
        return pd.DataFrame({col: pd.Series([], dtype="float64") for col in column_order})

    if df_of_subsequent_formatversion.empty:
        result_rows = [
            create_row(
                previous_df=df_of_previous_formatversion,
                subsequent_df=df_of_subsequent_formatversion,
                i=i,
                previous_formatversion=previous_formatversion,
                subsequent_formatversion=subsequent_formatversion,
            )
            for i in range(len(df_of_previous_formatversion))
        ]
        for row in result_rows:
            row["Änderung"] = "ENTFÄLLT"
            row["changed_entries"] = ""
        result_df = pd.DataFrame(result_rows)
        return result_df[column_order]

    if df_of_previous_formatversion.empty:
        result_rows = [
            create_row(
                previous_df=df_of_previous_formatversion,
                subsequent_df=df_of_subsequent_formatversion,
                j=j,
                previous_formatversion=previous_formatversion,
                subsequent_formatversion=subsequent_formatversion,
            )
            for j in range(len(df_of_subsequent_formatversion))
        ]
        for row in result_rows:
            row["Änderung"] = "NEU"
            row["changed_entries"] = ""
        result_df = pd.DataFrame(result_rows)
        return result_df[column_order]

    segments_of_previous_formatversion = df_of_previous_formatversion[f"Segmentname_{previous_formatversion}"].tolist()
    segments_of_subsequent_formatversion = df_of_subsequent_formatversion[
        f"Segmentname_{subsequent_formatversion}"
    ].tolist()
    result_rows = []

    i = 0
    j = 0

    # iterate through both lists until reaching their ends.
    while i < len(segments_of_previous_formatversion) or j < len(segments_of_subsequent_formatversion):
        if i >= len(segments_of_previous_formatversion):
            row = create_row(
                previous_df=df_of_previous_formatversion,
                subsequent_df=df_of_subsequent_formatversion,
                j=j,
                previous_formatversion=previous_formatversion,
                subsequent_formatversion=subsequent_formatversion,
            )
            row["Änderung"] = "NEU"
            row["changed_entries"] = ""
            result_rows.append(row)
            j += 1
        elif j >= len(segments_of_subsequent_formatversion):
            row = create_row(
                previous_df=df_of_previous_formatversion,
                subsequent_df=df_of_subsequent_formatversion,
                i=i,
                previous_formatversion=previous_formatversion,
                subsequent_formatversion=subsequent_formatversion,
            )
            row["Änderung"] = "ENTFÄLLT"
            row["changed_entries"] = ""
            result_rows.append(row)
            i += 1
        elif segments_of_previous_formatversion[i] == segments_of_subsequent_formatversion[j]:
            row = create_row(
                previous_df=df_of_previous_formatversion,
                subsequent_df=df_of_subsequent_formatversion,
                i=i,
                j=j,
                previous_formatversion=previous_formatversion,
                subsequent_formatversion=subsequent_formatversion,
            )

            # check for changes within one row.
            changed_entries = []
            has_changes = False

            # compare all columns except `Segmentname`.
            for col in columns_without_segmentname:
                # prevent "Unnamed" columns from being flagged with the "ÄNDERUNG" label.
                # "Unnamed" columns purpose is only to index through the rows (hidden in the XLSX output).
                if col.startswith("Unnamed:"):
                    continue

                prev_val = str(df_of_previous_formatversion.iloc[i][col])
                subs_val = str(df_of_subsequent_formatversion.iloc[j][col])

                # only consider cells/entries that are not empty for both formatversions.
                if prev_val.strip() and subs_val.strip() and prev_val != subs_val:
                    has_changes = True
                    changed_entries.extend([f"{col}_{previous_formatversion}", f"{col}_{subsequent_formatversion}"])

            row["Änderung"] = "ÄNDERUNG" if has_changes else ""
            row["changed_entries"] = "|".join(changed_entries) if changed_entries else ""
            result_rows.append(row)
            i += 1
            j += 1
        else:
            try:
                # try to find next matching value.
                next_match = segments_of_subsequent_formatversion[j:].index(segments_of_previous_formatversion[i])
                for k in range(next_match):
                    row = create_row(
                        previous_df=df_of_previous_formatversion,
                        subsequent_df=df_of_subsequent_formatversion,
                        j=j + k,
                        previous_formatversion=previous_formatversion,
                        subsequent_formatversion=subsequent_formatversion,
                    )
                    row["Änderung"] = "NEU"
                    row["changed_entries"] = ""
                    result_rows.append(row)
                j += next_match
            except ValueError:
                # no match found: add old value and empty new cell.
                row = create_row(
                    previous_df=df_of_previous_formatversion,
                    subsequent_df=df_of_subsequent_formatversion,
                    i=i,
                    previous_formatversion=previous_formatversion,
                    subsequent_formatversion=subsequent_formatversion,
                )
                row["Änderung"] = "ENTFÄLLT"
                row["changed_entries"] = ""
                result_rows.append(row)
                i += 1

    # create dataframe with NaN being replaced by empty strings.
    result_df = pd.DataFrame(result_rows).astype(str).replace("nan", "")
    return result_df[column_order]


# pylint:disable=too-many-branches, too-many-locals
def export_to_excel(df: DataFrame, output_path_xlsx: str) -> None:
    """
    exports the merged dataframe to .xlsx with highlighted differences.
    """
    sheet_name = Path(output_path_xlsx).stem  # excel sheet name = <pruefid>

    # add column for indexing through all rows.
    df = df.reset_index()
    df["index"] = df["index"] + 1
    df = df.rename(columns={"index": "#"})

    changed_entries_series = df["changed_entries"] if "changed_entries" in df.columns else pd.Series([""] * len(df))

    # remove duplicate columns that index through the rows.
    df_filtered = df[[col for col in df.columns if not col.startswith("Unnamed:") and col != "changed_entries"]]

    with pd.ExcelWriter(output_path_xlsx, engine="xlsxwriter") as writer:
        df_filtered.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # sticky table header
        worksheet.freeze_panes(1, 0)
        if not df_filtered.empty:
            table_options = {
                "style": "None",
                "columns": [{"header": col} for col in df_filtered.columns],
            }
            worksheet.add_table(0, 0, len(df_filtered), len(df_filtered.columns) - 1, table_options)

        # base formatting.
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D9D9D9", "border": 1, "align": "center", "text_wrap": True}
        )
        base_format = workbook.add_format({"border": 1, "text_wrap": True})

        # formatting highlighted/changed cells.
        diff_formats = {
            "NEU": workbook.add_format({"bg_color": "#C6EFCE", "border": 1, "text_wrap": True}),
            "ENTFÄLLT": workbook.add_format({"bg_color": "#FFC7CE", "border": 1, "text_wrap": True}),
            "ÄNDERUNG": workbook.add_format({"bg_color": "#F5DC98", "border": 1, "text_wrap": True}),
            "segmentname_changed": workbook.add_format({"bg_color": "#D9D9D9", "border": 1, "text_wrap": True}),
            "": workbook.add_format({"border": 1, "text_wrap": True}),
        }

        # formatting 'Änderung' column.
        diff_text_formats = {
            "NEU": workbook.add_format(
                {
                    "bold": True,
                    "color": "#7AAB8A",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "ENTFÄLLT": workbook.add_format(
                {
                    "bold": True,
                    "color": "#E94C74",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "ÄNDERUNG": workbook.add_format(
                {
                    "bold": True,
                    "color": "#B8860B",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "": workbook.add_format({"border": 1, "bg_color": "#D9D9D9", "align": "center", "text_wrap": True}),
        }

        segment_name_bold = workbook.add_format({"bold": True, "border": 1, "text_wrap": True, "bg_color": "#D9D9D9"})

        for col_num, value in enumerate(df_filtered.columns.values):
            worksheet.write(0, col_num, value, header_format)

        previous_formatversion = None
        subsequent_formatversion = None
        for col in df_filtered.columns:
            if col.startswith("Segmentname_"):
                suffix = col.split("Segmentname_")[1]
                if previous_formatversion is None:
                    previous_formatversion = suffix
                else:
                    subsequent_formatversion = suffix
                    break

        diff_idx = df_filtered.columns.get_loc("Änderung")
        previous_segmentname = None

        for row_num, row in enumerate(df_filtered.itertuples(index=False), start=1):
            row_data = list(row)
            diff_value = str(row_data[diff_idx])

            changed_entries = []
            if diff_value == "ÄNDERUNG":
                changed_entries_value = str(changed_entries_series.iloc[row_num - 1])
                if changed_entries_value != "nan":
                    changed_entries = changed_entries_value.split("|")

            # check if current `Segmentname` changed.
            current_segmentname = None
            segmentname_col = None
            for col_name in df_filtered.columns:
                if col_name.startswith("Segmentname_"):
                    idx = df_filtered.columns.get_loc(col_name)
                    value = str(row_data[idx])
                    if value:
                        current_segmentname = value
                        segmentname_col = col_name
                        break

            is_new_segment = current_segmentname and current_segmentname != previous_segmentname
            previous_segmentname = current_segmentname

            for col_num, (value, col_name) in enumerate(zip(row_data, df_filtered.columns)):
                value = str(value) if value != "" else ""

                if col_name == "Änderung":
                    worksheet.write(row_num, col_num, value, diff_text_formats[diff_value])
                elif (
                    diff_value == "ENTFÄLLT"
                    and previous_formatversion is not None
                    and isinstance(col_name, str)
                    and col_name.endswith(previous_formatversion)
                ):
                    worksheet.write(row_num, col_num, value, diff_formats["ENTFÄLLT"])
                elif (
                    diff_value == "NEU"
                    and subsequent_formatversion is not None
                    and isinstance(col_name, str)
                    and col_name.endswith(subsequent_formatversion)
                ):
                    worksheet.write(row_num, col_num, value, diff_formats["NEU"])
                elif diff_value == "ÄNDERUNG" and col_name in changed_entries:
                    worksheet.write(row_num, col_num, value, diff_formats["ÄNDERUNG"])
                elif is_new_segment and diff_value == "":
                    if col_name == segmentname_col:
                        worksheet.write(row_num, col_num, value, segment_name_bold)
                    else:
                        worksheet.write(row_num, col_num, value, diff_formats["segmentname_changed"])
                else:
                    worksheet.write(row_num, col_num, value, base_format)

        column_widths = {
            "#": 25,
            "Segmentname_": 175,
            "Segmentgruppe_": 100,
            "Segment_": 100,
            "Datenelement_": 100,
            "Segment ID_": 100,
            "Code_": 100,
            "Qualifier_": 100,
            "Beschreibung_": 150,
            "Bedingungsausdruck_": 100,
            "Bedingung_": 150,
        }

        for col_num, col_name in enumerate(df_filtered.columns):
            width_px = next(
                (width for prefix, width in column_widths.items() if col_name.startswith(prefix)), 150
            )  # default = 150 px
            excel_width = width_px / 7
            worksheet.set_column(col_num, col_num, excel_width)

        logger.info("✅successfully exported XLSX file to: %s", {output_path_xlsx})


def _process_files(
    previous_formatversion: str, subsequent_formatversion: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> None:
    """
    process all matching ahb/<pruefid>.csv files between two <formatversion> directories.
    """
    matching_files = get_matching_pruefid_files(previous_formatversion, subsequent_formatversion)

    if not matching_files:
        logger.warning("No matching files found to compare")
        return

    output_base = output_dir / f"{subsequent_formatversion}_{previous_formatversion}"

    for previous_pruefid, subsequent_pruefid, nachrichtentyp, pruefid in matching_files:
        logger.info("Processing %s - %s", nachrichtentyp, pruefid)

        try:
            df_of_previous_formatversion, df_of_subsequent_formatversion = _get_csv_content(
                previous_pruefid, subsequent_pruefid
            )
            merged_df = align_columns(
                df_of_previous_formatversion,
                df_of_subsequent_formatversion,
                previous_formatversion,
                subsequent_formatversion,
            )

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


def _process_submodule(output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    """
    processes all valid consecutive <formatversion> subdirectories.
    """
    logger.info("The output dir is %s", output_dir.absolute())
    consecutive_formatversions = determine_consecutive_formatversions()

    if not consecutive_formatversions:
        logger.warning("⚠️no valid consecutive formatversion subdirectories found to compare")
        return

    for subsequent_formatversion, previous_formatversion in consecutive_formatversions:
        logger.info(
            "⌛processing consecutive formatversions: %s -> %s", subsequent_formatversion, previous_formatversion
        )
        try:
            _process_files(previous_formatversion, subsequent_formatversion, output_dir)
        except (OSError, pd.errors.EmptyDataError, ValueError) as e:
            logger.error(
                "❌error processing formatversions %s -> %s: %s",
                subsequent_formatversion,
                previous_formatversion,
                str(e),
            )
            continue
