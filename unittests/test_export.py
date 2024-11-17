import os
import tempfile
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from ahb_diff.main import align_columns, export_to_excel


def test_export() -> None:
    """
    test csv and xlsx exports with example pruefid files.
    """
    test_data_dir = Path(__file__).parent / "test_data"

    pruefid_old = pd.read_csv(test_data_dir / "FV2410_55001.csv", dtype=str)
    pruefid_new = pd.read_csv(test_data_dir / "FV2504_55001.csv", dtype=str)

    df_merged = align_columns(pruefid_old, pruefid_new)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = temp_dir
        csv_path = Path(temp_dir) / "merge.csv"
        xlsx_path = Path(temp_dir) / "merge.xlsx"

        df_merged.to_csv(str(csv_path), index=False)
        export_to_excel(df_merged, str(xlsx_path))

        csv_df = pd.read_csv(csv_path, na_filter=False)
        assert_frame_equal(df_merged, csv_df)

        assert os.path.exists(xlsx_path)
        assert os.path.getsize(xlsx_path) > 0

    assert not os.path.exists(temp_dir_path)


def test_empty_dataframe_export() -> None:
    """test exporting an empty dataframe."""
    df = pd.DataFrame(columns=["Segmentname_old", "diff", "Segmentname_new"])

    with tempfile.TemporaryDirectory() as temp_dir:
        xlsx_path = Path(temp_dir) / "test.xlsx"
        export_to_excel(df, str(xlsx_path))

        assert os.path.exists(xlsx_path)
        assert os.path.getsize(xlsx_path) > 0
