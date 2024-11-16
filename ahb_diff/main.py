"""
functions to handle csv imports, comparison and exports.
"""

import os

import pandas as pd
from pandas.core.frame import DataFrame


def get_csv() -> tuple[DataFrame, DataFrame]:
    """
    read csv input files.
    """
    pruefid_old: DataFrame = pd.read_csv("unittests/test_data/pruefid_00001.csv", dtype=str)
    pruefid_new: DataFrame = pd.read_csv("unittests/test_data/pruefid_00002.csv", dtype=str)
    return pruefid_old, pruefid_new


def align_columns(pruefid_old: DataFrame, pruefid_new: DataFrame) -> DataFrame:
    """
    adds suffixes to `Segmentname` columns and aligns them by adding empty cells each time the cell values do not match.
    """
    # add suffixes to columns
    df_old = pruefid_old.add_suffix("_old")
    df_new = pruefid_new.add_suffix("_new")

    # get segments as lists
    segments_old = df_old["Segmentname_old"].tolist()
    segments_new = df_new["Segmentname_new"].tolist()

    aligned_column_old = []
    aligned_column_new = []
    i = 0
    j = 0

    # iterate through both lists until reaching their ends.
    while i < len(segments_old) or j < len(segments_new):
        if i >= len(segments_old):
            aligned_column_old.append("")
            aligned_column_new.append(segments_new[j])
            j += 1
        elif j >= len(segments_new):
            aligned_column_old.append(segments_old[i])
            aligned_column_new.append("")
            i += 1
        elif segments_old[i] == segments_new[j]:
            aligned_column_old.append(segments_old[i])
            aligned_column_new.append(segments_new[j])
            i += 1
            j += 1
        else:
            # try to find next matching value.
            try:
                next_match_new = segments_new[j:].index(segments_old[i])
                for _ in range(next_match_new):
                    aligned_column_old.append("")
                    aligned_column_new.append(segments_new[j])
                    j += 1
            # no match found: add old value and empty new cell.
            except ValueError:
                aligned_column_old.append(segments_old[i])
                aligned_column_new.append("")
                i += 1

    return pd.DataFrame(
        {
            "Segmentname_old": aligned_column_old,
            "diff": [""] * len(aligned_column_old),
            "Segmentname_new": aligned_column_new,
        }
    )


def merge_csv() -> DataFrame:
    """
    merges content of both input files into a single aligned DataFrame.
    """
    df_old, df_new = get_csv()
    return align_columns(df_old, df_new)


if __name__ == "__main__":
    pruefid_merged = merge_csv()

    os.makedirs("data/output", exist_ok=True)
    pruefid_merged.to_csv("data/output/ahb-diff.csv", index=False)
