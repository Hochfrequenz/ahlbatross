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
    pruefid_old: DataFrame = pd.read_csv("unittests/test_data/pruefid_00011.csv", dtype=str)
    pruefid_new: DataFrame = pd.read_csv("unittests/test_data/pruefid_00022.csv", dtype=str)
    return pruefid_old, pruefid_new


def create_row(
    old_df: DataFrame | None = None, new_df: DataFrame | None = None, i: int | None = None, j: int | None = None
) -> dict[str, Any]:
    """
    creates and fills rows for all columns that belong to one CSV depending on whether old/new segments already exist.
    """
    row = {"Segmentname_old": "", "Segmentname_new": "", "diff": ""}

    if old_df is not None and i is not None:
        row["Segmentname_old"] = old_df.iloc[i]["Segmentname_old"]
        for col in old_df.columns:
            if col != "Segmentname_old":
                row[col] = old_df.iloc[i][col]

    if new_df is not None and j is not None:
        row["Segmentname_new"] = new_df.iloc[j]["Segmentname_new"]
        for col in new_df.columns:
            if col != "Segmentname_new":
                row[col] = new_df.iloc[j][col]

    return row


def align_columns(pruefid_old: DataFrame, pruefid_new: DataFrame) -> DataFrame:
    """
    aligns `Segmentname` columns by adding empty cells each time the cell values do not match.
    """

    # add suffixes to columns
    df_old = pruefid_old.copy()
    df_new = pruefid_new.copy()
    df_old = df_old.rename(columns={"Segmentname": "Segmentname_old"})
    df_new = df_new.rename(columns={"Segmentname": "Segmentname_new"})

    segments_old = df_old["Segmentname_old"].tolist()
    segments_new = df_new["Segmentname_new"].tolist()
    result_rows = []

    i = 0
    j = 0

    # iterate through both lists until reaching their ends.
    while i < len(segments_old) or j < len(segments_new):
        if i >= len(segments_old):
            # Add remaining new segments
            result_rows.append(create_row(new_df=df_new, j=j))
            j += 1

        elif j >= len(segments_new):
            result_rows.append(create_row(old_df=df_old, i=i))
            i += 1

        elif segments_old[i] == segments_new[j]:
            result_rows.append(create_row(old_df=df_old, new_df=df_new, i=i, j=j))
            i += 1
            j += 1

        else:
            # try to find next matching value.
            try:
                next_match_new = segments_new[j:].index(segments_old[i])
                for _ in range(next_match_new):
                    result_rows.append(create_row(new_df=df_new, j=j))
                    j += 1
                continue
            except ValueError:
                # no match found: add old value and empty new cell.
                result_rows.append(create_row(old_df=df_old, i=i))
                i += 1

    result_df = pd.DataFrame(result_rows)

    # separate content of both CSV files by a diff column
    column_order = (
        ["Segmentname_old"]
        + [col for col in df_old.columns if col != "Segmentname_old"]
        + ["diff", "Segmentname_new"]
        + [col for col in df_new.columns if col != "Segmentname_new"]
    )

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
