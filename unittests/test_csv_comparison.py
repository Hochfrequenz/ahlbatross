import pandas as pd
from pandas.core.frame import DataFrame
from pandas.testing import assert_frame_equal

from ahb_diff.main import align_columns


def test_align_columns() -> None:

    old_pruefid = pd.DataFrame({"Segmentname": ["1", "2", "3", "4", "5", "6", "9", "10"]})
    new_pruefid = pd.DataFrame({"Segmentname": ["1", "2", "3", "5", "6", "7", "8", "9", "10"]})

    expected_output: DataFrame = pd.DataFrame(
        {
            "Segmentname_old": ["1", "2", "3", "4", "5", "6", "", "", "9", "10"],
            "diff": [""] * 10,
            "Segmentname_new": ["1", "2", "3", "", "5", "6", "7", "8", "9", "10"],
        }
    )

    output_df = align_columns(old_pruefid, new_pruefid)
    assert_frame_equal(output_df, expected_output)


def test_align_columns_empty_dataframes() -> None:

    old_pruefid: DataFrame = pd.DataFrame({"Segmentname": []})
    new_pruefid: DataFrame = pd.DataFrame({"Segmentname": []})

    expected_output: DataFrame = pd.DataFrame(
        {
            "Segmentname_old": [],
            "diff": [],
            "Segmentname_new": [],
        }
    )

    output_df = align_columns(old_pruefid, new_pruefid)
    assert_frame_equal(output_df, expected_output)


def test_align_columns_one_empty_dataframe() -> None:

    old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "3"]})
    new_pruefid: DataFrame = pd.DataFrame({"Segmentname": []})

    expected_output: DataFrame = pd.DataFrame(
        {
            "Segmentname_old": ["1", "2", "3"],
            "diff": [""] * 3,
            "Segmentname_new": ["", "", ""],
        }
    )

    output_df = align_columns(old_pruefid, new_pruefid)
    assert_frame_equal(output_df, expected_output)


def test_align_columns_full_offset() -> None:

    old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "3"]})
    new_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["4", "5", "6"]})

    expected_output: DataFrame = pd.DataFrame(
        {
            "Segmentname_old": ["1", "2", "3", "", "", ""],
            "diff": [""] * 6,
            "Segmentname_new": ["", "", "", "4", "5", "6"],
        }
    )

    output_df = align_columns(old_pruefid, new_pruefid)
    assert_frame_equal(output_df, expected_output)


def test_align_columns_duplicate_segments() -> None:

    old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "2"]})
    new_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "4"]})

    expected_output: DataFrame = pd.DataFrame(
        {
            "Segmentname_old": ["1", "2", "2", ""],
            "diff": [""] * 4,
            "Segmentname_new": ["1", "2", "", "4"],
        }
    )

    output_df = align_columns(old_pruefid, new_pruefid)
    assert_frame_equal(output_df, expected_output)


def test_align_columns_repeating_segments() -> None:

    old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "3", "3", "2"]})
    new_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "3", "4"]})

    expected_output: DataFrame = pd.DataFrame(
        {
            "Segmentname_old": ["1", "2", "3", "3", "2", ""],
            "diff": [""] * 6,
            "Segmentname_new": ["1", "2", "3", "", "", "4"],
        }
    )

    output_df = align_columns(old_pruefid, new_pruefid)
    assert_frame_equal(output_df, expected_output)
