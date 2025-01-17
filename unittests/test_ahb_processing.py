from pathlib import Path

import pytest
from efoli import EdifactFormatVersion

from ahlbatross.core.ahb_processing import get_formatversion_pairs, get_matching_csv_files


def test_parse_valid_formatversions() -> None:
    """
    test parsing of valid format version strings using efoli.
    """
    assert EdifactFormatVersion("FV2504") == EdifactFormatVersion.FV2504
    assert EdifactFormatVersion("FV2310") == EdifactFormatVersion.FV2310
    assert EdifactFormatVersion("FV2104") == EdifactFormatVersion.FV2104


def test_parse_invalid_formatversions() -> None:
    """
    test parsing of invalid formatversion strings.
    """
    test_cases = [
        "FV250",  # too short
        "FV25044",  # too long
        "FV2513",  # invalid month
        "FV2500",  # invalid month
        "XX2504",  # wrong prefix
        "",  # empty string
    ]

    for invalid_input in test_cases:
        with pytest.raises(ValueError):
            EdifactFormatVersion(invalid_input)


def test_get_matching_files(tmp_path: Path) -> None:
    """
    test find matching files across formatversions.
    """
    submodule: dict[str, dict[str, dict[str, str]]] = {
        "FV2504": {
            "nachrichtenformat_1": {"pruefid_1.csv": "content_1", "pruefid_2.csv": "content_2"},
            "nachrichtenformat_2": {"pruefid_1.csv": "content_1"},
        },
        "FV2410": {
            "nachrichtenformat_1": {"pruefid_1.csv": "content_1", "pruefid_2.csv": "content_2"},
            "nachrichtenformat_2": {"pruefid_3.csv": "content_3"},
        },
    }

    for formatversion, nachrichtenformate in submodule.items():
        formatversion_dir = tmp_path / formatversion
        formatversion_dir.mkdir()
        for nachrichtenformat, files in nachrichtenformate.items():
            nachrichtenformat_dir = formatversion_dir / nachrichtenformat / "csv"
            nachrichtenformat_dir.mkdir(parents=True)
            for file, content in files.items():
                (nachrichtenformat_dir / file).write_text(content)

    matches = get_matching_csv_files(
        root_dir=tmp_path,
        previous_formatversion=EdifactFormatVersion.FV2410,
        subsequent_formatversion=EdifactFormatVersion.FV2504,
    )

    assert len(matches) == 2
    assert matches[0][2] == "nachrichtenformat_1"
    assert matches[0][3] == "pruefid_1"
    assert matches[1][3] == "pruefid_2"


def test_determine_consecutive_formatversions(tmp_path: Path) -> None:
    """
    test successful determination of consecutive formatversions.
    """
    submodule: dict[str, dict[str, bool | dict[str, str]]] = {
        "FV2504": {"nachrichtenformat_1": True},
        "FV2410": {"nachrichtenformat_1": True},
        "FV2404": {},
        "FV2310": {"nachrichtenformat_1": True},
    }

    for formatversion, nachrichtenformate in submodule.items():
        formatversion_dir = tmp_path / formatversion
        formatversion_dir.mkdir()
        for nachrichtenformat, has_csv in nachrichtenformate.items():
            nachrichtenformat_dir = formatversion_dir / nachrichtenformat
            nachrichtenformat_dir.mkdir()
            if has_csv:
                csv_dir = nachrichtenformat_dir / "csv"
                csv_dir.mkdir()
                (csv_dir / "test.csv").write_text("test")

    result = get_formatversion_pairs(root_dir=tmp_path)
    expected = [(EdifactFormatVersion.FV2504, EdifactFormatVersion.FV2410)]
    assert result == expected
