import shutil
from pathlib import Path
from typing import Any, Callable, ContextManager

import py7zr
import pytest
from efoli import EdifactFormatVersion
from fundamend.sqlmodels import AhbTabellenLine
from sqlalchemy.engine import Engine
from sqlmodel import Session, func, select
from syrupy.assertion import SnapshotAssertion
from typer.testing import CliRunner

from ahlbatross.core.ahb_diff import (
    compare_ahb_across_format_versions,
    compare_all_pruefidentifikators,
    get_all_comparison_candidates,
    get_common_pruefidentifikators,
    populate_comparison_tables,
)
from ahlbatross.db import get_anwendungsfall_from_db
from ahlbatross.db.sqlmodels import AhbComparisonSummaryTable, AhbLineComparisonTable
from ahlbatross.enums.diff_types import DiffType
from ahlbatross.main import app
from ahlbatross.models.ahb import AhbLineComparison


def test_ahb_database_can_be_opened(
    unencrypted_ahb_database: Path,
    create_disposed_engine: Callable[[Path], ContextManager[Engine]],
) -> None:
    """Test that the decrypted AHB database can be opened and queried."""
    with create_disposed_engine(unencrypted_ahb_database) as engine:
        with Session(engine) as session:
            row_count = session.exec(select(func.count()).select_from(AhbTabellenLine)).one()
            assert row_count > 0


def test_read_single_ahb_from_database(unencrypted_ahb_database: Path) -> None:
    """Test that we can read AHB lines from the database using get_anwendungsfall_from_db."""
    ahb_lines = get_anwendungsfall_from_db(
        db_path=unencrypted_ahb_database,
        edifact_format_version=EdifactFormatVersion.FV2504,
        pruefidentifikator="55001",
    )
    assert len(ahb_lines) > 0

    segment_codes = [line.segment_code for line in ahb_lines if line.segment_code]
    unh_index = segment_codes.index("UNH")
    unt_index = segment_codes.index("UNT")
    assert unh_index < unt_index


def test_compare_ahb_across_format_versions(unencrypted_ahb_database: Path) -> None:
    """Test comparing the same Prüfidentifikator across different format versions."""
    pruefidentifikator = "55001"

    comparison = compare_ahb_across_format_versions(
        db_path=unencrypted_ahb_database,
        previous_format_version=EdifactFormatVersion.FV2410,
        subsequent_format_version=EdifactFormatVersion.FV2504,
        pruefidentifikator=pruefidentifikator,
    )

    assert comparison.pruefidentifikator == pruefidentifikator
    assert comparison.previous_format_version == EdifactFormatVersion.FV2410
    assert comparison.subsequent_format_version == EdifactFormatVersion.FV2504

    summary = comparison.summary
    expected_total = summary.unchanged_count + summary.modified_count + summary.added_count + summary.removed_count
    assert summary.total_lines == expected_total
    assert summary.total_lines > 0

    assert len(comparison.line_comparisons) == summary.total_lines

    for line_comp in comparison.line_comparisons:
        if line_comp.diff_type == DiffType.ADDED:
            assert line_comp.previous_line is None
            assert line_comp.subsequent_line is not None
        elif line_comp.diff_type == DiffType.REMOVED:
            assert line_comp.previous_line is not None
            assert line_comp.subsequent_line is None
        else:
            assert line_comp.previous_line is not None
            assert line_comp.subsequent_line is not None
            if line_comp.diff_type == DiffType.MODIFIED:
                assert len(line_comp.changed_fields) > 0


def test_get_common_pruefidentifikators(unencrypted_ahb_database: Path) -> None:
    """Test finding common Prüfidentifikators across format versions."""
    common_pruefis = get_common_pruefidentifikators(
        db_path=unencrypted_ahb_database,
        previous_format_version=EdifactFormatVersion.FV2410,
        subsequent_format_version=EdifactFormatVersion.FV2504,
    )
    assert len(common_pruefis) > 0
    assert "55001" in common_pruefis


def test_compare_all_pruefidentifikators(
    unencrypted_ahb_database: Path,
    tmp_path: Path,
    create_disposed_engine: Callable[[Path], ContextManager[Engine]],
) -> None:
    """Test comparing all Prüfidentifikators and storing results in database."""
    output_db_path = tmp_path / "comparison_results.db"

    comparison_count = compare_all_pruefidentifikators(
        db_path=unencrypted_ahb_database,
        previous_format_version=EdifactFormatVersion.FV2410,
        subsequent_format_version=EdifactFormatVersion.FV2504,
        output_db_path=output_db_path,
    )

    assert comparison_count > 0
    assert output_db_path.exists()

    with create_disposed_engine(output_db_path) as engine:
        with Session(engine) as session:
            summaries = session.exec(select(AhbComparisonSummaryTable)).all()
            assert len(summaries) == comparison_count

            line_comparisons = session.exec(select(AhbLineComparisonTable)).all()
            assert len(line_comparisons) > 0

            valid_diff_types = [d.value for d in DiffType]
            for line_comp in line_comparisons[:10]:
                assert line_comp.id_path is not None
                assert line_comp.diff_type in valid_diff_types


def test_populate_comparison_tables(
    unencrypted_ahb_database: Path,
    tmp_path: Path,
    create_disposed_engine: Callable[[Path], ContextManager[Engine]],
) -> None:
    """Test populating comparison tables for all format version pairs."""
    test_db_path = tmp_path / "ahb_with_comparisons.db"
    shutil.copy(unencrypted_ahb_database, test_db_path)

    total_comparisons = populate_comparison_tables(test_db_path)

    assert total_comparisons > 0

    with create_disposed_engine(test_db_path) as engine:
        with Session(engine) as session:
            summaries = session.exec(select(AhbComparisonSummaryTable)).all()
            assert len(summaries) == total_comparisons

            line_comparisons = session.exec(select(AhbLineComparisonTable)).all()
            assert len(line_comparisons) > 0

            distinct_version_pairs = session.exec(
                select(
                    AhbComparisonSummaryTable.previous_format_version,
                    AhbComparisonSummaryTable.subsequent_format_version,
                ).distinct()
            ).all()
            assert len(distinct_version_pairs) >= 1

            modified_lines = session.exec(
                select(AhbLineComparisonTable).where(AhbLineComparisonTable.diff_type == DiffType.MODIFIED.value)
            ).all()
            assert modified_lines is not None


@pytest.mark.snapshot
def test_compare_ahb_snapshot(unencrypted_ahb_database: Path, snapshot: SnapshotAssertion) -> None:
    """Snapshot test for AHB comparison output."""
    comparison = compare_ahb_across_format_versions(
        db_path=unencrypted_ahb_database,
        previous_format_version=EdifactFormatVersion.FV2410,
        subsequent_format_version=EdifactFormatVersion.FV2504,
        pruefidentifikator="55001",
    )

    def build_comparison_entry(lc: AhbLineComparison) -> dict[str, Any]:
        """Build a detailed comparison entry including field changes."""
        entry: dict[str, Any] = {
            "id_path": lc.id_path,
            "diff_type": lc.diff_type.value,
        }
        if lc.diff_type == DiffType.MODIFIED and lc.changed_fields and lc.previous_line and lc.subsequent_line:
            entry["field_changes"] = {
                field: {
                    "previous": getattr(lc.previous_line, field, None),
                    "subsequent": getattr(lc.subsequent_line, field, None),
                }
                for field in lc.changed_fields
            }
        elif lc.diff_type == DiffType.ADDED and lc.subsequent_line:
            # Show what was added
            entry["added_values"] = {
                "segment_code": lc.subsequent_line.segment_code,
                "data_element": lc.subsequent_line.data_element,
                "description": lc.subsequent_line.description,
            }
        elif lc.diff_type == DiffType.REMOVED and lc.previous_line:
            # Show what was removed
            entry["removed_values"] = {
                "segment_code": lc.previous_line.segment_code,
                "data_element": lc.previous_line.data_element,
                "description": lc.previous_line.description,
            }
        return entry

    snapshot_data = {
        "pruefidentifikator": comparison.pruefidentifikator,
        "previous_format_version": comparison.previous_format_version.value,
        "subsequent_format_version": comparison.subsequent_format_version.value,
        "summary": {
            "total_lines": comparison.summary.total_lines,
            "unchanged_count": comparison.summary.unchanged_count,
            "modified_count": comparison.summary.modified_count,
            "added_count": comparison.summary.added_count,
            "removed_count": comparison.summary.removed_count,
        },
        "sample_comparisons": [build_comparison_entry(lc) for lc in comparison.line_comparisons],
    }

    assert snapshot_data == snapshot


@pytest.mark.snapshot
def test_comparison_candidates_snapshot(unencrypted_ahb_database: Path, snapshot: SnapshotAssertion) -> None:
    """Snapshot test for all comparison candidates (format version pairs with their Prüfidentifikators)."""
    # Group candidates by format version pair since the generator now yields individual pruefis
    grouped: dict[tuple[str, str], list[str]] = {}
    for prev_fv, subseq_fv, pruefi in get_all_comparison_candidates(unencrypted_ahb_database):
        key = (prev_fv.value, subseq_fv.value)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(pruefi)

    snapshot_data = {
        "total_comparisons": sum(len(pruefis) for pruefis in grouped.values()),
        "format_version_pairs": [
            {
                "previous_format_version": prev_fv,
                "subsequent_format_version": subseq_fv,
                "pruefidentifikators": pruefis,
                "count": len(pruefis),
            }
            for (prev_fv, subseq_fv), pruefis in sorted(grouped.items())
        ],
    }

    assert snapshot_data == snapshot


def test_populate_db_cli(
    tmp_path: Path,
    create_disposed_engine: Callable[[Path], ContextManager[Engine]],
) -> None:
    """Test the populate-db CLI command with a copy of the unencrypted 7z archive."""
    source_7z = Path(__file__).parent / "test_data" / "ahb.db.7z"
    if not source_7z.exists():
        pytest.skip("ahb.db.7z not found in test_data")

    test_7z = tmp_path / "ahb.db.7z"
    shutil.copy(source_7z, test_7z)

    runner = CliRunner()
    result = runner.invoke(app, [str(test_7z)])

    assert result.exit_code == 0
    assert "Successfully" in result.stdout or "Created" in result.stdout

    with py7zr.SevenZipFile(test_7z, mode="r") as archive:
        archive.extractall(path=tmp_path / "extracted")

    extracted_db = tmp_path / "extracted" / "ahb.db"
    assert extracted_db.exists()

    with create_disposed_engine(extracted_db) as engine:
        with Session(engine) as session:
            summaries = session.exec(select(AhbComparisonSummaryTable)).all()
            assert len(summaries) > 0

            line_comparisons = session.exec(select(AhbLineComparisonTable)).all()
            assert len(line_comparisons) > 0
