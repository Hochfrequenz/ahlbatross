"""
AHB csv comparison logic.
"""

from typing import Any, List, Tuple

import pandas as pd
from pandas.core.frame import DataFrame

from ahlbatross.enums.diff_types import DiffType
from ahlbatross.models.ahb import AhbRow, AhbRowComparison, AhbRowDiff
from ahlbatross.utils.string_formatting import normalize_entries


def _populate_row_entries(
    df: DataFrame | None,
    row: dict[str, Any],
    idx: int | None,
    formatversion: str,
    is_segmentname: bool = True,
) -> None:
    """
    Populate row entries for a given dataframe segment.
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
    Fills rows for all columns that belong to one dataframe depending on whether previous/subsequent segments exist.
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


# pylint:disable=too-many-branches, too-many-statements, too-many-locals
def align_columns(
    previous_pruefid: DataFrame,
    subsequent_pruefid: DataFrame,
    previous_formatversion: str,
    subsequent_formatversion: str,
) -> DataFrame:
    """
    Aligns `Segmentname` columns by adding empty cells each time the cell values do not match.
    During comparison, whitespaces are removed while preserving original values for the output.
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

    # get all unique columns from both dataframes
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

    # add corresponding formatversions as suffixes to columns
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

    # iterate through both lists until reaching their ends
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

            # check for changes within one row
            changed_entries = []
            has_changes = False

            # compare all columns except `Segmentname`
            for col in columns_without_segmentname:
                # prevent "Unnamed" columns from being flagged with the "ÄNDERUNG" label
                # "unnamed" columns purpose is only to index through the rows (hidden in the XLSX output)
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
                # try to find next matching value
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
                # no match found: add old value and empty new cell
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

    # create dataframe with NaN being replaced by empty strings
    result_df = pd.DataFrame(result_rows).astype(str).replace("nan", "")
    return result_df[column_order]


def _compare_ahb_rows(previous_ahb_row: AhbRow, subsequent_ahb_row: AhbRow) -> AhbRowDiff:
    """
    Compare two AhbRow objects to identify changes.
    """
    changed_entries = []

    # consider all AHB properties except `section_name` (Segmentname) and `formatversion`
    ahb_properties = [
        "segment_group_key",
        "segment_code",
        "data_element",
        "segment_id",
        "value_pool_entry",
        "name",
        "ahb_expression",
        "conditions",
    ]

    for entry in ahb_properties:
        previous_ahb_entry = getattr(previous_ahb_row, entry, "") or ""
        subsequent_ahb_entry = getattr(subsequent_ahb_row, entry, "") or ""

        if (previous_ahb_entry.strip() or subsequent_ahb_entry.strip()) and previous_ahb_entry != subsequent_ahb_entry:
            changed_entries.extend(
                [f"{entry}_{previous_ahb_row.formatversion}", f"{entry}_{subsequent_ahb_row.formatversion}"]
            )

    return AhbRowDiff(
        diff_type=DiffType.MODIFIED if changed_entries else DiffType.UNCHANGED, changed_entries=changed_entries
    )


def _add_empty_row(formatversion: str) -> AhbRow:
    """
    Create an empty row.
    """
    return AhbRow(
        formatversion=formatversion,
        section_name="",
        segment_group_key=None,
        segment_code=None,
        data_element=None,
        segment_id=None,
        value_pool_entry=None,
        name=None,
        ahb_expression=None,
        conditions=None,
    )


def _find_matching_subsequent_row(
    current_ahb_row: AhbRow, subsequent_ahb_rows: List[AhbRow], start_idx: int
) -> Tuple[int, AhbRow | None]:
    """
    Find matching row in subsequent version starting from given index.
    """
    normalized_current = normalize_entries(current_ahb_row.section_name)

    for idx, row in enumerate(subsequent_ahb_rows[start_idx:], start_idx):
        if normalize_entries(row.section_name) == normalized_current:
            return idx, row
    return -1, None


def align_ahb_rows(previous_ahb_rows: List[AhbRow], subsequent_ahb_rows: List[AhbRow]) -> List[AhbRowComparison]:
    """
    Align AHB rows while comparing two formatversions.
    """
    result = []
    i = 0
    j = 0

    while i < len(previous_ahb_rows) or j < len(subsequent_ahb_rows):
        if i >= len(previous_ahb_rows):
            row = subsequent_ahb_rows[j]
            result.append(
                AhbRowComparison(
                    previous_formatversion=_add_empty_row(row.formatversion),
                    # label remaining rows of subsequent AHB as NEW
                    diff=AhbRowDiff(diff_type=DiffType.ADDED),
                    subsequent_formatversion=row,
                )
            )
            j += 1

        elif j >= len(subsequent_ahb_rows):
            row = previous_ahb_rows[i]
            result.append(
                AhbRowComparison(
                    previous_formatversion=row,
                    # label remaining rows of previous AHB as REMOVED
                    diff=AhbRowDiff(diff_type=DiffType.REMOVED),
                    subsequent_formatversion=_add_empty_row(row.formatversion),
                )
            )
            i += 1

        else:
            current_row = previous_ahb_rows[i]
            next_match_idx, matching_row = _find_matching_subsequent_row(current_row, subsequent_ahb_rows, j)

            if next_match_idx >= 0 and matching_row is not None:
                # add new rows until `section_name` (Segmentname) matches
                for k in range(j, next_match_idx):
                    new_row = subsequent_ahb_rows[k]
                    result.append(
                        AhbRowComparison(
                            previous_formatversion=_add_empty_row(new_row.formatversion),
                            diff=AhbRowDiff(diff_type=DiffType.ADDED),
                            subsequent_formatversion=new_row,
                        )
                    )

                # add matching rows with comparison
                diff = _compare_ahb_rows(current_row, matching_row)
                result.append(
                    AhbRowComparison(
                        previous_formatversion=current_row, diff=diff, subsequent_formatversion=matching_row
                    )
                )

                i += 1
                j = next_match_idx + 1

            else:
                # if no match found - label as REMOVED
                result.append(
                    AhbRowComparison(
                        previous_formatversion=current_row,
                        diff=AhbRowDiff(diff_type=DiffType.REMOVED),
                        subsequent_formatversion=_add_empty_row(current_row.formatversion),
                    )
                )
                i += 1

    return result
