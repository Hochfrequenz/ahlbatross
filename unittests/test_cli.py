import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ahlbatross.main import app


def test_input_output_path(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """
    test CLI handling of "--input-dir"/"-i" and "--output-dir"/"-o" directory paths.
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
    long_form_flag = runner.invoke(
        app, ["compare", "--input-dir", str(input_dir), "--output-dir", str(output_dir)], catch_exceptions=False
    )
    short_form_flag = runner.invoke(
        app, ["compare", "-i", str(input_dir), "-o", str(output_dir)], catch_exceptions=False
    )

    assert long_form_flag.exit_code == 0
    assert short_form_flag.exit_code == 0
    assert str(output_dir.absolute()) in caplog.text


def test_invalid_input_output_path(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """
    test CLI handling of invalid "--input-dir"/"-i" and "--output-dir"/"-o" directory paths.
    """
    caplog.set_level(logging.INFO)
    invalid_dir = tmp_path / "does_not_exist"
    runner = CliRunner()
    result = runner.invoke(
        app, ["compare", "--input-dir", str(invalid_dir), "--output-dir", str(tmp_path)], catch_exceptions=False
    )

    assert "❌ Input directory does not exist:" in caplog.text
    assert str(invalid_dir) in caplog.text
    assert result.exit_code == 1
