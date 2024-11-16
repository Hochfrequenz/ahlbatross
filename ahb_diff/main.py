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


def align_columns(merged_df: DataFrame) -> DataFrame:
    """
    aligns "Segmentname" columns by adding empty cells each time the cell values do not match.
    """
    old_col = "Segmentname_old"
    new_col = "Segmentname_new"

    # create lists comprising the content for both columns, respectively.
    old_segments = merged_df[old_col].tolist()
    new_segments = merged_df[new_col].tolist()

    aligned_old = []
    aligned_new = []
    i = 0
    j = 0

    # iterate through both lists until reaching their ends.
    while i < len(old_segments) or j < len(new_segments):
        if i >= len(old_segments):
            aligned_old.append("")
            aligned_new.append(new_segments[j])
            j += 1
        elif j >= len(new_segments):
            aligned_old.append(old_segments[i])
            aligned_new.append("")
            i += 1
        elif old_segments[i] == new_segments[j]:
            aligned_old.append(old_segments[i])
            aligned_new.append(new_segments[j])
            i += 1
            j += 1
        else:
            # try to find next matching value.
            try:
                next_match_new = new_segments[j:].index(old_segments[i])
                for _ in range(next_match_new):
                    aligned_old.append("")
                    aligned_new.append(new_segments[j])
                    j += 1
            except ValueError:
                # no match found: add old value and empty new cell.
                aligned_old.append(old_segments[i])
                aligned_new.append("")
                i += 1

    aligned_df = pd.DataFrame({old_col: aligned_old, "diff": [""] * len(aligned_old), new_col: aligned_new})

    return aligned_df


def merge_csv() -> DataFrame:
    """
    merges content of both input files into a single dataFrame.
    """
    pruefid_old, pruefid_new = get_csv()

    pruefid_old = pruefid_old.add_suffix("_old")
    pruefid_new = pruefid_new.add_suffix("_new")

    pruefid_diff = pd.DataFrame({"diff": [""] * len(pruefid_old)})

    merged_df: DataFrame = pd.concat([pruefid_old, pruefid_diff, pruefid_new], axis=1)
    aligned_df = align_columns(merged_df)

    return aligned_df


if __name__ == "__main__":
    pruefid_merged = merge_csv()

    os.makedirs("data/output", exist_ok=True)
    pruefid_merged.to_csv("data/output/ahb-diff.csv", index=False)
