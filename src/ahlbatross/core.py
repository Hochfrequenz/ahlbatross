"""
AHB data fetching and parsing as well as csv imports, processing and exports.
"""

from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd
from pandas.core.frame import DataFrame
from xlsxwriter.format import Format  # type:ignore[import-untyped]

from ahlbatross.formats.csv import get_csv_files, load_csv_dataframes
from ahlbatross.formats.excel import export_to_excel
from ahlbatross.logger import logger
from ahlbatross.utils import normalize_entries, parse_formatversions

XlsxFormat: TypeAlias = Format


def _is_formatversion_dir(path: Path) -> bool:
    """
    confirm if path is a <formatversion> directory - for instance "FV2504/".
    """
    return path.is_dir() and path.name.startswith("FV") and len(path.name) == 6


def _is_formatversion_dir_empty(root_dir: Path, formatversion: str) -> bool:
    """
    check if a <formatversion> directory does not contain any <nachrichtenformat> directories.
    """
    formatversion_dir = root_dir / formatversion
    if not formatversion_dir.exists():
        return True

    return len(_get_nachrichtenformat_dirs(formatversion_dir)) == 0


def _get_formatversion_dirs(root_dir: Path) -> list[str]:
    """
    fetch all available <formatversion> directories, sorted from latest to oldest.
    """
    if not root_dir.exists():
        raise FileNotFoundError(f"❌ Submodule / base directory does not exist: {root_dir}")

    formatversion_dirs = [d.name for d in root_dir.iterdir() if _is_formatversion_dir(d)]
    formatversion_dirs.sort(key=parse_formatversions, reverse=True)
    return formatversion_dirs


def _get_nachrichtenformat_dirs(formatversion_dir: Path) -> list[Path]:
    """
    fetch all <nachrichtenformat> directories that contain actual csv files.
    """
    if not formatversion_dir.exists():
        raise FileNotFoundError(f"❌ Formatversion directory not found: {formatversion_dir.absolute()}")

    return [d for d in formatversion_dir.iterdir() if d.is_dir() and (d / "csv").exists() and (d / "csv").is_dir()]


def get_formatversion_pairs(root_dir: Path) -> list[tuple[str, str]]:
    """
    generate pairs of consecutive <formatversion> directories.
    """
    formatversion_list = _get_formatversion_dirs(root_dir)
    formatversion_pairs = []

    for i in range(len(formatversion_list) - 1):
        subsequent_formatversion = formatversion_list[i]
        previous_formatversion = formatversion_list[i + 1]

        # skip if at least one <formatversion> directory is empty.
        if _is_formatversion_dir_empty(root_dir, subsequent_formatversion) or _is_formatversion_dir_empty(
            root_dir, previous_formatversion
        ):
            logger.warning(
                "❗️Skipping empty consecutive formatversions: %s -> %s",
                subsequent_formatversion,
                previous_formatversion,
            )
            continue

        formatversion_pairs.append((subsequent_formatversion, previous_formatversion))

    return formatversion_pairs


# pylint:disable=too-many-locals
def get_matching_csv_files(
    root_dir: Path, previous_formatversion: str, subsequent_formatversion: str
) -> list[tuple[Path, Path, str, str]]:
    """
    find matching <pruefid>.csv files across <formatversion>/<nachrichtenformat> directories.
    """
    previous_formatversion_dir = root_dir / previous_formatversion
    subsequent_formatversion_dir = root_dir / subsequent_formatversion

    if not all(d.exists() for d in [previous_formatversion_dir, subsequent_formatversion_dir]):
        logger.error("❌ At least one formatversion directory does not exist.")
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

        previous_files = {f.stem: f for f in get_csv_files(previous_csv_dir)}
        subsequent_files = {f.stem: f for f in get_csv_files(subsequent_csv_dir)}

        common_ahbs = set(previous_files.keys()) & set(subsequent_files.keys())

        for pruefid in sorted(common_ahbs):
            matching_files.append((previous_files[pruefid], subsequent_files[pruefid], nachrichtentyp, pruefid))

    return matching_files


def _populate_row_entries(
    df: DataFrame | None,
    row: dict[str, Any],
    idx: int | None,
    formatversion: str,
    is_segmentname: bool = True,
) -> None:
    """
    populate row entries for a given dataframe segment.
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

    _populate_row_entries(previous_df, row, i, previous_formatversion, is_segmentname=True)
    _populate_row_entries(subsequent_df, row, j, subsequent_formatversion, is_segmentname=True)

    _populate_row_entries(previous_df, row, i, previous_formatversion, is_segmentname=False)
    _populate_row_entries(subsequent_df, row, j, subsequent_formatversion, is_segmentname=False)

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
    during comparison, whitespaces are removed while preserving original values for the output.
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

    # normalize `Segmentname` columns values by removing any whitespace
    segments_of_previous_formatversion_normalized = [
        normalize_entries(s) if isinstance(s, str) else s
        for s in df_of_previous_formatversion[f"Segmentname_{previous_formatversion}"].tolist()
    ]
    segments_of_subsequent_formatversion_normalized = [
        normalize_entries(s) if isinstance(s, str) else s
        for s in df_of_subsequent_formatversion[f"Segmentname_{subsequent_formatversion}"].tolist()
    ]

    # keep original `Segmentname` values for output
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
        elif segments_of_previous_formatversion_normalized[i] == segments_of_subsequent_formatversion_normalized[j]:
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

                # consider a change when (1) at least one value is non-empty AND (2) the values are different
                if (prev_val.strip() or subs_val.strip()) and prev_val != subs_val:
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
                next_match = -1
                for k, subsequent_value in enumerate(segments_of_subsequent_formatversion_normalized[j:], start=j):
                    if subsequent_value == segments_of_previous_formatversion_normalized[i]:
                        next_match = k - j
                        break

                if next_match >= 0:
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
                else:
                    raise ValueError("no match found.")
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


def _process_files(
    root_dir: Path, previous_formatversion: str, subsequent_formatversion: str, output_dir: Path
) -> None:
    """
    process all matching ahb/<pruefid>.csv files between two <formatversion> directories.
    """
    matching_files = get_matching_csv_files(root_dir, previous_formatversion, subsequent_formatversion)

    if not matching_files:
        logger.warning("No matching files found to compare")
        return

    output_base = output_dir / f"{subsequent_formatversion}_{previous_formatversion}"

    for previous_pruefid, subsequent_pruefid, nachrichtentyp, pruefid in matching_files:
        logger.info("Processing %s - %s", nachrichtentyp, pruefid)

        try:
            df_of_previous_formatversion, df_of_subsequent_formatversion = load_csv_dataframes(
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

            logger.info("✅ Successfully processed %s/%s", nachrichtentyp, pruefid)

        except pd.errors.EmptyDataError:
            logger.error("❌ Empty or corrupted CSV file for %s/%s", nachrichtentyp, pruefid)
        except OSError as e:
            logger.error("❌ File system error for %s/%s: %s", nachrichtentyp, pruefid, str(e))
        except ValueError as e:
            logger.error("❌ Data processing error for %s/%s: %s", nachrichtentyp, pruefid, str(e))


def process_ahb_files(input_dir: Path, output_dir: Path) -> None:
    """
    processes subdirectories of all valid consecutive <formatversion> pairs.
    """
    logger.info("Found AHB root directory at: %s", input_dir.absolute())
    logger.info("Output directory: %s", output_dir.absolute())

    consecutive_formatversions = get_formatversion_pairs(input_dir)

    if not consecutive_formatversions:
        logger.warning("❗️ No valid consecutive formatversion subdirectories found to compare.")
        return

    for subsequent_formatversion, previous_formatversion in consecutive_formatversions:
        logger.info(
            "⌛ Processing consecutive formatversions: %s -> %s", subsequent_formatversion, previous_formatversion
        )
        try:
            _process_files(
                root_dir=input_dir,
                previous_formatversion=previous_formatversion,
                subsequent_formatversion=subsequent_formatversion,
                output_dir=output_dir,
            )
        except (OSError, pd.errors.EmptyDataError, ValueError) as e:
            logger.error(
                "❌ Error processing formatversions %s -> %s: %s",
                subsequent_formatversion,
                previous_formatversion,
                str(e),
            )
            continue
