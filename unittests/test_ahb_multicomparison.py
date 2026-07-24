from pathlib import Path
from unittest.mock import patch

import pytest

from ahlbatross.core import ahb_multicomparison
from ahlbatross.core.ahb_multicomparison import find_pid, get_pids, multicompare_command

AHB_CSV_HEADER = (
    "Segmentname,Segmentgruppe,Segment,Datenelement,Segment ID,"
    "Code,Qualifier,Beschreibung,Bedingungsausdruck,Bedingung\n"
)
AHB_CSV_ROW = "Nachrichten-Kopfsegment,SG1,TST,0001,00001,E_0001,,Description,Muss,[1] Condition"


@pytest.fixture(autouse=True)
def _clear_pid_cache() -> None:
    """
    the module-level PID cache must not leak state between tests.
    """
    ahb_multicomparison._FORMATVERSION_PID_CACHE.clear()  # pylint: disable=protected-access


def _write_ahb_csv(csv_dir: Path, pruefid: str) -> None:
    csv_dir.mkdir(parents=True, exist_ok=True)
    (csv_dir / f"{pruefid}.csv").write_text(AHB_CSV_HEADER + AHB_CSV_ROW)


def test_find_pid_missing_formatversion_dir(tmp_path: Path) -> None:
    """
    test that find_pid returns None when the formatversion directory does not exist.
    """
    assert find_pid(tmp_path, "FV2504", "pruefid_1") is None


def test_find_pid_skips_nachrichtenformat_without_csv_dir(tmp_path: Path) -> None:
    """
    test that find_pid ignores nachrichtenformat directories without a csv subdirectory.
    """
    (tmp_path / "FV2504" / "nachrichtenformat_without_csv").mkdir(parents=True)
    _write_ahb_csv(tmp_path / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_1")

    result = find_pid(tmp_path, "FV2504", "pruefid_1")

    assert result is not None
    file_path, nf_name = result
    assert file_path.name == "pruefid_1.csv"
    assert nf_name == "nachrichtenformat_1"


def test_find_pid_uses_cache_on_second_call(tmp_path: Path) -> None:
    """
    test that a second find_pid call for the same formatversion reuses the cache instead of re-scanning.
    """
    _write_ahb_csv(tmp_path / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_1")

    first_result = find_pid(tmp_path, "FV2504", "pruefid_1")
    # remove the underlying file to prove the second lookup is served from the cache
    (tmp_path / "FV2504" / "nachrichtenformat_1" / "csv" / "pruefid_1.csv").unlink()
    second_result = find_pid(tmp_path, "FV2504", "pruefid_1")

    assert first_result == second_result


def test_find_pid_unknown_pruefid(tmp_path: Path) -> None:
    """
    test that find_pid returns None for a pruefid that does not exist in the formatversion.
    """
    _write_ahb_csv(tmp_path / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_1")

    assert find_pid(tmp_path, "FV2504", "does_not_exist") is None


def test_get_pids_returns_sorted_unique_pids(tmp_path: Path) -> None:
    """
    test that get_pids returns all available pruefids for a formatversion, sorted.
    """
    _write_ahb_csv(tmp_path / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_2")
    _write_ahb_csv(tmp_path / "FV2504" / "nachrichtenformat_2" / "csv", "pruefid_1")

    assert get_pids(tmp_path, "FV2504") == ["pruefid_1", "pruefid_2"]


def test_get_pids_missing_formatversion(tmp_path: Path) -> None:
    """
    test that get_pids returns an empty list for a formatversion that does not exist.
    """
    assert get_pids(tmp_path, "FV2504") == []


def test_multicompare_command_input_dir_missing(tmp_path: Path) -> None:
    """
    test that multicompare_command exits with code 1 when the input directory does not exist.
    """
    with pytest.raises(SystemExit) as exc_info:
        multicompare_command(tmp_path / "does_not_exist", tmp_path / "output")

    assert exc_info.value.code == 1


def test_multicompare_command_no_formatversions(tmp_path: Path) -> None:
    """
    test that multicompare_command exits with code 1 when no formatversion directories are found.
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        multicompare_command(input_dir, tmp_path / "output")

    assert exc_info.value.code == 1


def test_multicompare_command_aborts_without_second_pid(tmp_path: Path) -> None:
    """
    test that pressing enter (empty FV) on the second comparison aborts with exit code 1
    since no comparisons were collected.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    _write_ahb_csv(input_dir / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_1")

    with patch("ahlbatross.core.ahb_multicomparison.Prompt.ask", side_effect=["FV2504", "pruefid_1", ""]):
        with pytest.raises(SystemExit) as exc_info:
            multicompare_command(input_dir, output_dir)

    assert exc_info.value.code == 1


def test_multicompare_command_exports_xlsx(tmp_path: Path) -> None:
    """
    test the full interactive happy path: two PIDs are selected and exported into a single xlsx file.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    _write_ahb_csv(input_dir / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_1")
    _write_ahb_csv(input_dir / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_2")

    responses = ["FV2504", "pruefid_1", "FV2504", "pruefid_2", ""]
    with patch("ahlbatross.core.ahb_multicomparison.Prompt.ask", side_effect=responses):
        multicompare_command(input_dir, output_dir)

    xlsx_path = output_dir / "pruefid_1_comparisons.xlsx"
    assert xlsx_path.exists()
    assert xlsx_path.stat().st_size > 0


def test_multicompare_command_retries_invalid_fv_and_pid(tmp_path: Path) -> None:
    """
    test that invalid FV and PID inputs are rejected and re-prompted before a valid selection succeeds.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    _write_ahb_csv(input_dir / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_1")
    _write_ahb_csv(input_dir / "FV2504" / "nachrichtenformat_1" / "csv", "pruefid_2")

    responses = [
        "FV9999",  # invalid FV, retried
        "FV2504",
        "invalid_pid",  # invalid PID, retried
        "pruefid_1",
        "FV2504",
        "pruefid_1",  # same PID+FV as first selection, rejected
        "pruefid_2",
        "",
    ]
    with patch("ahlbatross.core.ahb_multicomparison.Prompt.ask", side_effect=responses):
        multicompare_command(input_dir, output_dir)

    xlsx_path = output_dir / "pruefid_1_comparisons.xlsx"
    assert xlsx_path.exists()


def test_multicompare_command_no_pids_in_selected_fv(tmp_path: Path) -> None:
    """
    test that multicompare_command exits with code 1 if the selected FV directory has no PIDs.
    """
    input_dir = tmp_path / "input"
    (input_dir / "FV2504").mkdir(parents=True)

    with patch("ahlbatross.core.ahb_multicomparison.Prompt.ask", side_effect=["FV2504"]):
        with pytest.raises(SystemExit) as exc_info:
            multicompare_command(input_dir, tmp_path / "output")

    assert exc_info.value.code == 1
