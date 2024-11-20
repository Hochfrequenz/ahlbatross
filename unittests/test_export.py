import logging
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from typer.testing import CliRunner

from ahlbatross.cli import app
from ahlbatross.excel import export_to_excel
from ahlbatross.main import align_columns


def test_export() -> None:
    """
    test csv and xlsx exports with example pruefid files.
    """
    test_data_dir = Path(__file__).parent / "test_data"

    previous_formatversion = "FV2410"
    subsequent_formatversion = "FV2504"

    pruefid_old = pd.read_csv(test_data_dir / f"{previous_formatversion}_55001.csv", dtype=str)
    pruefid_new = pd.read_csv(test_data_dir / f"{subsequent_formatversion}_55001.csv", dtype=str)

    df_merged = align_columns(
        pruefid_old,
        pruefid_new,
        previous_formatversion=previous_formatversion,
        subsequent_formatversion=subsequent_formatversion,
    )

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
    """
    test exporting an empty dataframe.
    """
    previous_formatversion = "FV2410"
    subsequent_formatversion = "FV2504"

    df = pd.DataFrame(
        columns=[f"Segmentname_{previous_formatversion}", "Änderung", f"Segmentname_{subsequent_formatversion}"]
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        xlsx_path = Path(temp_dir) / "test.xlsx"
        export_to_excel(df, str(xlsx_path))

        assert os.path.exists(xlsx_path)
        assert os.path.getsize(xlsx_path) > 0


def test_cli_with_custom_output_directory(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """
    test CLI handling of custom --output-dir.
    """
    caplog.set_level(logging.INFO)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    fv_dir = input_dir / "FV2504" / "Nachrichtenformat_1"
    fv_dir.mkdir(parents=True)
    csv_dir = fv_dir / "csv"
    csv_dir.mkdir()
    (csv_dir / "test.csv").write_text("test data")

    output_dir = tmp_path / "custom_output"
    output_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        app, ["--input-dir", str(input_dir), "--output-dir", str(output_dir)], catch_exceptions=False
    )

    assert result.exit_code == 0
    assert str(output_dir.absolute()) in caplog.text
