import pandas as pd
from pandas.core.frame import DataFrame
from pandas.testing import assert_frame_equal

from ahb_diff.main import align_columns


class TestSingleColumnDataframes:
    """
    test cases for dataframes containing only a `Segmentname` column.
    """

    def test_align_columns(self) -> None:

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

    def test_align_columns_empty_dataframes(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame({"Segmentname": []})
        new_pruefid: DataFrame = pd.DataFrame({"Segmentname": []})

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": pd.Series([], dtype="float64"),
                "diff": pd.Series([], dtype="float64"),
                "Segmentname_new": pd.Series([], dtype="float64"),
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_one_empty_dataframe(self) -> None:

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

    def test_align_columns_full_offset(self) -> None:

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

    def test_align_columns_duplicate_segments(self) -> None:

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

    def test_align_columns_repeating_segments(self) -> None:

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


class TestMultiColumnDataFrames:
    """
    test cases for dataframes containing multiple columns in addition to `Segmentname`.
    """

    def test_align_columns(self) -> None:
        old_pruefid = pd.DataFrame(
            {
                "Segmentname": ["1", "2", "3", "4", "5", "6", "9", "10"],
                "Segmentgruppe": ["a", "b", "c", "", "e", "f", "g", "h"],
            }
        )
        new_pruefid = pd.DataFrame(
            {
                "Segmentname": ["1", "2", "3", "5", "6", "7", "8", "9", "10"],
                "Segmentgruppe": ["a", "b", "d", "d", "d", "e", "f", "a", "b"],
            }
        )

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": ["1", "2", "3", "4", "5", "6", "", "", "9", "10"],
                "Segmentgruppe_old": ["a", "b", "c", "", "e", "f", "", "", "g", "h"],
                "diff": [""] * 10,
                "Segmentname_new": ["1", "2", "3", "", "5", "6", "7", "8", "9", "10"],
                "Segmentgruppe_new": ["a", "b", "d", "", "d", "d", "e", "f", "a", "b"],
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_empty_dataframes(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame({"Segmentname": [], "Segmentgruppe": []})
        new_pruefid: DataFrame = pd.DataFrame({"Segmentname": [], "Segmentgruppe": []})

        expected_output: DataFrame = pd.DataFrame(
            {"Segmentname_old": [], "Segmentgruppe_old": [], "diff": [], "Segmentname_new": [], "Segmentgruppe_new": []}
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_one_empty_dataframe(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "3"], "Segmentgruppe": ["a", "b", "c"]})
        new_pruefid: DataFrame = pd.DataFrame({"Segmentname": [], "Segmentgruppe": []})

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": ["1", "2", "3"],
                "Segmentgruppe_old": ["a", "b", "c"],
                "diff": [""] * 3,
                "Segmentname_new": ["", "", ""],
                "Segmentgruppe_new": ["", "", ""],
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_full_offset(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "3"], "Segmentgruppe": ["a", "b", "c"]})
        new_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["4", "5", "6"], "Segmentgruppe": ["d", "e", "f"]})

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": ["1", "2", "3", "", "", ""],
                "Segmentgruppe_old": ["a", "b", "c", "", "", ""],
                "diff": [""] * 6,
                "Segmentname_new": ["", "", "", "4", "5", "6"],
                "Segmentgruppe_new": ["", "", "", "d", "e", "f"],
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_duplicate_segments(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "2"], "Segmentgruppe": ["a", "b", "c"]})
        new_pruefid: DataFrame = pd.DataFrame({"Segmentname": ["1", "2", "4"], "Segmentgruppe": ["a", "b", "d"]})

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": ["1", "2", "2", ""],
                "Segmentgruppe_old": ["a", "b", "c", ""],
                "diff": [""] * 4,
                "Segmentname_new": ["1", "2", "", "4"],
                "Segmentgruppe_new": ["a", "b", "", "d"],
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_repeating_segments(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame(
            {"Segmentname": ["1", "2", "3", "3", "2"], "Segmentgruppe": ["a", "b", "c", "d", "e"]}
        )
        new_pruefid: DataFrame = pd.DataFrame(
            {"Segmentname": ["1", "2", "3", "4"], "Segmentgruppe": ["a", "b", "c", "d"]}
        )

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": ["1", "2", "3", "3", "2", ""],
                "Segmentgruppe_old": ["a", "b", "c", "d", "e", ""],
                "diff": [""] * 6,
                "Segmentname_new": ["1", "2", "3", "", "", "4"],
                "Segmentgruppe_new": ["a", "b", "c", "", "", "d"],
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)

    def test_align_columns_different_column_sets(self) -> None:
        old_pruefid: DataFrame = pd.DataFrame(
            {
                "Segmentname": ["1", "2"],
                "Segmentgruppe": ["a", "b"],
                "Datenelement": ["x", "y"],
                "Qualifier": ["XY", "YZ"],
            }
        )
        new_pruefid: DataFrame = pd.DataFrame(
            {
                "Segmentname": ["2", "3"],
                "Segmentgruppe": ["b", "c"],
                "Datenelement": ["m", "n"],
                "Qualifier": ["XY", ""],
            }
        )

        expected_output: DataFrame = pd.DataFrame(
            {
                "Segmentname_old": ["1", "2", ""],
                "Segmentgruppe_old": ["a", "b", ""],
                "Datenelement_old": ["x", "y", ""],
                "Qualifier_old": ["XY", "YZ", ""],
                "diff": [""] * 3,
                "Segmentname_new": ["", "2", "3"],
                "Segmentgruppe_new": ["", "b", "c"],
                "Datenelement_new": ["", "m", "n"],
                "Qualifier_new": ["", "XY", ""],
            }
        )

        output_df = align_columns(old_pruefid, new_pruefid)
        assert_frame_equal(output_df, expected_output)
