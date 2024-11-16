"""
functions to handle csv imports, comparison and exports.
"""

import os
from typing import Any

import pandas as pd
from pandas.core.frame import DataFrame


def get_csv() -> tuple[DataFrame, DataFrame]:
    """
    read csv input files.
    """
    pruefid_old: DataFrame = pd.read_csv(
        "data/machine-readable_anwendungshandbuecher/FV2410/UTILMD/csv/55003.csv", dtype=str
    )
    pruefid_new: DataFrame = pd.read_csv(
        "data/machine-readable_anwendungshandbuecher/FV2504/UTILMD/csv/55003.csv", dtype=str
    )
    return pruefid_old, pruefid_new


def create_row(
    old_df: DataFrame | None = None, new_df: DataFrame | None = None, i: int | None = None, j: int | None = None
) -> dict[str, Any]:
    """
    fills rows for all columns that belong to one dataframe depending on whether old/new segments already exist.
    """
    row = {"Segmentname_old": "", "diff": "", "Segmentname_new": ""}

    if old_df is not None:
        for col in old_df.columns:
            if col != "Segmentname_old":
                row[f"{col}_old"] = ""

    if new_df is not None:
        for col in new_df.columns:
            if col != "Segmentname_new":
                row[f"{col}_new"] = ""

    if old_df is not None and i is not None:
        row["Segmentname_old"] = old_df.iloc[i]["Segmentname_old"]
        for col in old_df.columns:
            if col != "Segmentname_old":
                value = old_df.iloc[i][col]
                row[f"{col}_old"] = "" if pd.isna(value) else value

    if new_df is not None and j is not None:
        row["Segmentname_new"] = new_df.iloc[j]["Segmentname_new"]
        for col in new_df.columns:
            if col != "Segmentname_new":
                value = new_df.iloc[j][col]
                row[f"{col}_new"] = "" if pd.isna(value) else value

    return row


# pylint:disable=too-many-statements
def align_columns(pruefid_old: DataFrame, pruefid_new: DataFrame) -> DataFrame:
    """
    aligns `Segmentname` columns by adding empty cells each time the cell values do not match.
    """
    # add suffixes to columns.
    df_old = pruefid_old.copy()
    df_new = pruefid_new.copy()
    df_old = df_old.rename(columns={"Segmentname": "Segmentname_old"})
    df_new = df_new.rename(columns={"Segmentname": "Segmentname_new"})

    # preserve column order.
    old_columns = [col for col in pruefid_old.columns if col != "Segmentname"]
    new_columns = [col for col in pruefid_new.columns if col != "Segmentname"]

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
        result_rows = [create_row(old_df=df_old, new_df=df_new, i=i) for i in range(len(df_old))]
        for row in result_rows:
            row["diff"] = "REMOVED"
        result_df = pd.DataFrame(result_rows)
        return result_df[column_order]

    if df_old.empty:
        result_rows = [create_row(old_df=df_old, new_df=df_new, j=j) for j in range(len(df_new))]
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
            row = create_row(old_df=df_old, new_df=df_new, j=j)
            row["diff"] = "NEW"
            result_rows.append(row)
            j += 1
        elif j >= len(segments_new):
            row = create_row(old_df=df_old, new_df=df_new, i=i)
            row["diff"] = "REMOVED"
            result_rows.append(row)
            i += 1
        elif segments_old[i] == segments_new[j]:
            row = create_row(old_df=df_old, new_df=df_new, i=i, j=j)
            row["diff"] = ""
            result_rows.append(row)
            i += 1
            j += 1
        else:
            # try to find next matching value.
            try:
                next_match_new = segments_new[j:].index(segments_old[i])
                for _ in range(next_match_new):
                    row = create_row(old_df=df_old, new_df=df_new, j=j)
                    row["diff"] = "NEW"
                    result_rows.append(row)
                    j += 1
                continue
            except ValueError:
                # no match found: add old value and empty new cell.
                row = create_row(old_df=df_old, new_df=df_new, i=i)
                row["diff"] = "REMOVED"  # Segment only in old file
                result_rows.append(row)
                i += 1

    # create dataframe with string dtype and replace NaN with empty strings.
    result_df = pd.DataFrame(result_rows).astype(str).replace("nan", "")
    return result_df[column_order]


def merge_csv() -> DataFrame:
    """
    merges content of both input files into a single aligned dataframe.
    """
    df_old, df_new = get_csv()
    return align_columns(df_old, df_new)


if __name__ == "__main__":
    pruefid_merged = merge_csv()

    os.makedirs("data/output", exist_ok=True)
    pruefid_merged.to_csv("data/output/ahb-diff.csv", index=False)
