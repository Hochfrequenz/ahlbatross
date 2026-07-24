import csv
import tempfile
from pathlib import Path
from typing import List

import pytest

from ahlbatross.enums.diff_types import DiffType
from ahlbatross.formats.csv import export_to_csv, get_csv_files, load_csv_files
from ahlbatross.models.ahb import AhbRow, AhbRowComparison, AhbRowDiff

AHB_CSV_HEADER = (
    "Segmentname,Segmentgruppe,Segment,Datenelement,Segment ID,"
    "Code,Qualifier,Beschreibung,Bedingungsausdruck,Bedingung\n"
)


def test_get_csv_files_nonexistent_dir(tmp_path: Path) -> None:
    """
    test that a non-existent csv directory returns an empty list instead of raising.
    """
    assert get_csv_files(tmp_path / "does_not_exist") == []


def test_get_csv_files_returns_sorted_csvs(tmp_path: Path) -> None:
    """
    test that only *.csv files are returned, sorted by name.
    """
    (tmp_path / "b.csv").write_text("b")
    (tmp_path / "a.csv").write_text("a")
    (tmp_path / "ignored.txt").write_text("ignored")

    files = get_csv_files(tmp_path)

    assert [f.name for f in files] == ["a.csv", "b.csv"]


def test_export_to_csv(tmp_path: Path, ahb_row_comparison_single_column: List[AhbRowComparison]) -> None:
    """
    test that comparisons are exported to csv with correct headers and row content.
    """
    csv_path = tmp_path / "export.csv"

    export_to_csv(ahb_row_comparison_single_column, csv_path)

    assert csv_path.exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    assert header[0] == "#"
    assert "Änderung" in header
    assert len(rows) == len(ahb_row_comparison_single_column) + 1

    first_data_row = rows[1]
    first_comp = ahb_row_comparison_single_column[0]
    assert first_data_row[0] == "1"
    assert first_data_row[1] == first_comp.previous_formatversion.section_name
    assert first_data_row[9] == first_comp.diff.diff_type.value


def test_export_to_csv_handles_none_values(tmp_path: Path) -> None:
    """
    test that None values on AhbRow are exported as empty strings.
    """
    comparisons = [
        AhbRowComparison(
            previous_formatversion=AhbRow(formatversion="FV2410", section_name=None, value_pool_entry=None, name=None),
            diff=AhbRowDiff(diff_type=DiffType.UNCHANGED),
            subsequent_formatversion=AhbRow(
                formatversion="FV2504", section_name=None, value_pool_entry=None, name=None
            ),
        )
    ]
    csv_path = tmp_path / "export.csv"

    export_to_csv(comparisons, csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[1][1] == ""


def test_load_csv_files() -> None:
    """
    Test loading of <pruefid>.csv files.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        previous_ahb_csv = temp_dir_path / "previous_pruefid.csv"
        with open(previous_ahb_csv, "w", encoding="utf-8") as f:
            f.write(AHB_CSV_HEADER)
            f.write("Nachrichten-Kopfsegment,SG1,TST,0001,00001,E_0001,,Description 1,Muss,[1] Condition")

        subsequent_ahb_csv = temp_dir_path / "subsequent_pruefid.csv"
        with open(subsequent_ahb_csv, "w", encoding="utf-8") as f:
            f.write(AHB_CSV_HEADER)
            f.write("Nachrichten-Kopfsegment,SG2,TST,0001,00001,E_0002,,Description 2,Muss,[2] Condition")

        previous_ahb_rows, subsequent_ahb_rows = load_csv_files(
            previous_ahb_csv, subsequent_ahb_csv, previous_formatversion="FV2410", subsequent_formatversion="FV2504"
        )

        assert len(previous_ahb_rows) == 1
        assert len(subsequent_ahb_rows) == 1

        assert isinstance(previous_ahb_rows[0], AhbRow)
        assert isinstance(subsequent_ahb_rows[0], AhbRow)

        assert previous_ahb_rows[0].section_name == "Nachrichten-Kopfsegment"
        assert previous_ahb_rows[0].segment_group_key == "SG1"
        assert previous_ahb_rows[0].segment_code == "TST"
        assert previous_ahb_rows[0].data_element == "0001"
        assert previous_ahb_rows[0].segment_id == "00001"
        assert previous_ahb_rows[0].value_pool_entry == "E_0001"
        assert previous_ahb_rows[0].name == "Description 1"
        assert previous_ahb_rows[0].ahb_expression == "Muss"
        assert previous_ahb_rows[0].conditions == "[1] Condition"
        assert previous_ahb_rows[0].formatversion == "FV2410"

        assert subsequent_ahb_rows[0].section_name == "Nachrichten-Kopfsegment"
        assert subsequent_ahb_rows[0].segment_group_key == "SG2"
        assert subsequent_ahb_rows[0].segment_code == "TST"
        assert subsequent_ahb_rows[0].data_element == "0001"
        assert subsequent_ahb_rows[0].segment_id == "00001"
        assert subsequent_ahb_rows[0].value_pool_entry == "E_0002"
        assert subsequent_ahb_rows[0].name == "Description 2"
        assert subsequent_ahb_rows[0].ahb_expression == "Muss"
        assert subsequent_ahb_rows[0].conditions == "[2] Condition"
        assert subsequent_ahb_rows[0].formatversion == "FV2504"


def test_load_empty_csv() -> None:
    """
    Test loading empty <pruefid>.csv files that contain only headers.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        previous_ahb_csv = temp_dir_path / "previous_pruefid.csv"
        with open(previous_ahb_csv, "w", encoding="utf-8") as f:
            f.write(AHB_CSV_HEADER)

        subsequent_ahb_csv = temp_dir_path / "subsequent_pruefid.csv"
        with open(subsequent_ahb_csv, "w", encoding="utf-8") as f:
            f.write(AHB_CSV_HEADER)

        previous_ahb_rows, subsequent_ahb_rows = load_csv_files(
            previous_ahb_csv, subsequent_ahb_csv, previous_formatversion="FV2410", subsequent_formatversion="FV2504"
        )

        assert len(previous_ahb_rows) == 0
        assert len(subsequent_ahb_rows) == 0


def test_load_csv_missing_optional_fields() -> None:
    """
    Test loading <pruefid>.csv with missing optional AHB properties.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        previous_ahb_csv = temp_dir_path / "previous_pruefid.csv"
        with open(previous_ahb_csv, "w", encoding="utf-8") as f:
            f.write("Segmentname\n")
            f.write("Nachrichten-Kopfsegment")

        subsequent_ahb_csv = temp_dir_path / "subsequent_pruefid.csv"
        with open(subsequent_ahb_csv, "w", encoding="utf-8") as f:
            f.write("Segmentname\n")
            f.write("Nachrichten-Kopfsegment")

        previous_ahb_rows, subsequent_ahb_rows = load_csv_files(
            previous_ahb_csv,
            subsequent_ahb_csv,
            previous_formatversion="FV2410",
            subsequent_formatversion="FV2504",
        )

        assert len(previous_ahb_rows) == 1
        assert len(subsequent_ahb_rows) == 1

        assert previous_ahb_rows[0].segment_group_key is None
        assert previous_ahb_rows[0].segment_code is None
        assert previous_ahb_rows[0].data_element is None
        assert previous_ahb_rows[0].segment_id is None
        assert previous_ahb_rows[0].value_pool_entry is None
        assert previous_ahb_rows[0].name is None
        assert previous_ahb_rows[0].ahb_expression is None
        assert previous_ahb_rows[0].conditions is None

        assert subsequent_ahb_rows[0].segment_group_key is None
        assert subsequent_ahb_rows[0].segment_code is None
        assert subsequent_ahb_rows[0].data_element is None
        assert subsequent_ahb_rows[0].segment_id is None
        assert subsequent_ahb_rows[0].value_pool_entry is None
        assert subsequent_ahb_rows[0].name is None
        assert subsequent_ahb_rows[0].ahb_expression is None
        assert subsequent_ahb_rows[0].conditions is None


def test_load_csv_without_segmentname_column() -> None:
    """
    Test attempt loading <pruefid>.csv with missing `section_name` (Segmentname) column.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        previous_ahb_csv = temp_dir_path / "previous_pruefid.csv"
        with open(previous_ahb_csv, "w", encoding="utf-8") as f:
            f.write("Segmentgruppe\n")
            f.write("SG1")

        subsequent_ahb_csv = temp_dir_path / "subsequent_pruefid.csv"
        with open(subsequent_ahb_csv, "w", encoding="utf-8") as f:
            f.write("Segmentgruppe\n")
            f.write("SG2")

        with pytest.raises(KeyError):
            load_csv_files(
                previous_ahb_csv,
                subsequent_ahb_csv,
                previous_formatversion="FV2410",
                subsequent_formatversion="FV2504",
            )
