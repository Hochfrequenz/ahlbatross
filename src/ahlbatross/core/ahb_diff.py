"""Compare AHB data across format versions."""

import logging
from collections import Counter
from collections.abc import Iterator
from itertools import groupby
from pathlib import Path

from efoli import EdifactFormatVersion
from fundamend.sqlmodels import AhbTabellenLine
from sqlmodel import Session, SQLModel, create_engine, select, text

from ahlbatross.db import get_anwendungsfall_from_db
from ahlbatross.db.sqlmodels import AhbComparisonSummaryTable, AhbLineComparisonTable
from ahlbatross.enums.diff_types import DiffType
from ahlbatross.models.ahb import AhbComparison, AhbComparisonSummary, AhbLineComparison

logger = logging.getLogger(__name__)

# Fields to compare for detecting modifications (excluding metadata fields)
_COMPARISON_FIELDS = [
    "description",
    "segmentgroup_key",
    "segment_code",
    "data_element",
    "qualifier",
    "line_ahb_status",
    "line_name",
    "line_type",
    "bedingung",
]


def _get_changed_fields(previous: AhbTabellenLine, subsequent: AhbTabellenLine) -> list[str]:
    """Determine which fields changed between two lines."""
    return [field for field in _COMPARISON_FIELDS if getattr(previous, field, None) != getattr(subsequent, field, None)]


def _compare_single_line(
    id_path: str,
    previous_line: AhbTabellenLine | None,
    subsequent_line: AhbTabellenLine | None,
) -> tuple[AhbLineComparison, DiffType]:
    """Compare a single line and return the comparison result with its diff type."""
    if previous_line is None and subsequent_line is not None:
        diff_type = DiffType.ADDED
        changed_fields: list[str] = []
    elif previous_line is not None and subsequent_line is None:
        diff_type = DiffType.REMOVED
        changed_fields = []
    else:
        assert previous_line is not None and subsequent_line is not None
        changed_fields = _get_changed_fields(previous_line, subsequent_line)
        diff_type = DiffType.MODIFIED if changed_fields else DiffType.UNCHANGED

    return (
        AhbLineComparison(
            id_path=id_path,
            diff_type=diff_type,
            previous_line=previous_line,
            subsequent_line=subsequent_line,
            changed_fields=changed_fields,
        ),
        diff_type,
    )


def _get_sort_key(comp: AhbLineComparison) -> tuple[str, str]:
    """Get sort key for a line comparison: (previous_sort_path, subsequent_sort_path)."""
    prev_sort_path = comp.previous_line.sort_path or "" if comp.previous_line else ""
    subseq_sort_path = comp.subsequent_line.sort_path or "" if comp.subsequent_line else ""
    return (prev_sort_path, subseq_sort_path)


def compare_ahb_across_format_versions(
    db_path: Path,
    previous_format_version: EdifactFormatVersion,
    subsequent_format_version: EdifactFormatVersion,
    pruefidentifikator: str,
) -> AhbComparison:
    """
    Compare an AHB (Prüfidentifikator) across two format versions.

    Args:
        db_path: Path to the SQLite database file.
        previous_format_version: The earlier EDIFACT format version.
        subsequent_format_version: The later EDIFACT format version.
        pruefidentifikator: The Prüfidentifikator to compare.

    Returns:
        AhbComparison containing all line comparisons and summary statistics.
    """
    previous_lines = get_anwendungsfall_from_db(
        db_path=db_path,
        edifact_format_version=previous_format_version,
        pruefidentifikator=pruefidentifikator,
    )
    subsequent_lines = get_anwendungsfall_from_db(
        db_path=db_path,
        edifact_format_version=subsequent_format_version,
        pruefidentifikator=pruefidentifikator,
    )

    previous_by_id_path: dict[str, AhbTabellenLine] = {line.id_path: line for line in previous_lines}
    subsequent_by_id_path: dict[str, AhbTabellenLine] = {line.id_path: line for line in subsequent_lines}
    all_id_paths = set(previous_by_id_path.keys()) | set(subsequent_by_id_path.keys())

    line_comparisons: list[AhbLineComparison] = []
    diff_type_counts: Counter[DiffType] = Counter()

    for id_path in all_id_paths:
        comparison, diff_type = _compare_single_line(
            id_path,
            previous_by_id_path.get(id_path),
            subsequent_by_id_path.get(id_path),
        )
        line_comparisons.append(comparison)
        diff_type_counts[diff_type] += 1

    line_comparisons.sort(key=_get_sort_key)

    # pylint: disable=no-member
    summary = AhbComparisonSummary(
        total_lines=len(all_id_paths),
        unchanged_count=diff_type_counts[DiffType.UNCHANGED],
        modified_count=diff_type_counts[DiffType.MODIFIED],
        added_count=diff_type_counts[DiffType.ADDED],
        removed_count=diff_type_counts[DiffType.REMOVED],
    )

    return AhbComparison(
        pruefidentifikator=pruefidentifikator,
        previous_format_version=previous_format_version,
        subsequent_format_version=subsequent_format_version,
        summary=summary,
        line_comparisons=line_comparisons,
    )


def get_common_pruefidentifikators(
    db_path: Path,
    previous_format_version: EdifactFormatVersion,
    subsequent_format_version: EdifactFormatVersion,
) -> list[str]:
    """
    Get all Prüfidentifikators that exist in both format versions.

    Args:
        db_path: Path to the SQLite database file.
        previous_format_version: The earlier EDIFACT format version.
        subsequent_format_version: The later EDIFACT format version.

    Returns:
        List of Prüfidentifikators present in both versions.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        prev_pruefis_stmt = (
            select(AhbTabellenLine.pruefidentifikator)
            .where(AhbTabellenLine.format_version == previous_format_version)
            .distinct()
        )
        subseq_pruefis_stmt = (
            select(AhbTabellenLine.pruefidentifikator)
            .where(AhbTabellenLine.format_version == subsequent_format_version)
            .distinct()
        )

        prev_pruefis = {row for row in session.exec(prev_pruefis_stmt).all() if row}
        subseq_pruefis = {row for row in session.exec(subseq_pruefis_stmt).all() if row}

        return sorted(prev_pruefis & subseq_pruefis)


def compare_all_pruefidentifikators(
    db_path: Path,
    previous_format_version: EdifactFormatVersion,
    subsequent_format_version: EdifactFormatVersion,
    output_db_path: Path,
) -> int:
    """
    Compare all Prüfidentifikators that exist in both format versions and store results in a database.

    Args:
        db_path: Path to the source SQLite database file with AHB data.
        previous_format_version: The earlier EDIFACT format version.
        subsequent_format_version: The later EDIFACT format version.
        output_db_path: Path to the output SQLite database for storing comparisons.

    Returns:
        Number of Prüfidentifikators compared.
    """
    common_pruefis = get_common_pruefidentifikators(db_path, previous_format_version, subsequent_format_version)

    output_engine = create_engine(f"sqlite:///{output_db_path}")
    SQLModel.metadata.create_all(output_engine)

    with Session(output_engine) as session:
        for pruefi in common_pruefis:
            comparison = compare_ahb_across_format_versions(
                db_path=db_path,
                previous_format_version=previous_format_version,
                subsequent_format_version=subsequent_format_version,
                pruefidentifikator=pruefi,
            )

            # pylint: disable=no-member
            summary_row = AhbComparisonSummaryTable(
                pruefidentifikator=pruefi,
                previous_format_version=previous_format_version.value,
                subsequent_format_version=subsequent_format_version.value,
                total_lines=comparison.summary.total_lines,
                unchanged_count=comparison.summary.unchanged_count,
                modified_count=comparison.summary.modified_count,
                added_count=comparison.summary.added_count,
                removed_count=comparison.summary.removed_count,
            )
            session.add(summary_row)

            # Store line comparisons
            for line_comp in comparison.line_comparisons:
                line_row = AhbLineComparisonTable(
                    pruefidentifikator=pruefi,
                    previous_format_version=previous_format_version.value,
                    subsequent_format_version=subsequent_format_version.value,
                    id_path=line_comp.id_path,
                    diff_type=line_comp.diff_type.value,
                    previous_line_id=str(line_comp.previous_line.id) if line_comp.previous_line else None,
                    subsequent_line_id=str(line_comp.subsequent_line.id) if line_comp.subsequent_line else None,
                    changed_fields=",".join(line_comp.changed_fields) if line_comp.changed_fields else None,
                )
                session.add(line_row)

        session.commit()

    return len(common_pruefis)


def get_all_format_versions(db_path: Path) -> list[EdifactFormatVersion]:
    """
    Get all distinct format versions present in the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of EdifactFormatVersion sorted chronologically.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        stmt = select(AhbTabellenLine.format_version).distinct().order_by(AhbTabellenLine.format_version)
        results = session.exec(stmt).all()
        return [EdifactFormatVersion(fv) if isinstance(fv, str) else fv for fv in results]


def _get_pruefis_by_format_version(db_path: Path) -> dict[EdifactFormatVersion, set[str]]:
    """Load all pruefidentifikators grouped by format version."""
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        distinct_fv_pruefi_pairs = select(
            AhbTabellenLine.format_version,
            AhbTabellenLine.pruefidentifikator,
        ).distinct()
        results = session.exec(distinct_fv_pruefi_pairs).all()

        pruefis_by_format_version: dict[EdifactFormatVersion, set[str]] = {}
        for format_version, pruefi in results:
            if not pruefi:
                continue
            fv = (
                format_version
                if isinstance(format_version, EdifactFormatVersion)
                else EdifactFormatVersion(format_version)
            )
            if fv not in pruefis_by_format_version:
                pruefis_by_format_version[fv] = set()
            pruefis_by_format_version[fv].add(pruefi)

        return pruefis_by_format_version


def get_all_comparison_candidates(
    db_path: Path,
) -> Iterator[tuple[EdifactFormatVersion, EdifactFormatVersion, str]]:
    """
    Yield all distinct combinations of (previous_format_version, subsequent_format_version, pruefidentifikator)
    that can be compared based on the v_ahbtabellen data.

    This generator yields one tuple per comparison candidate (format version pair + single pruefidentifikator),
    sorted by format versions (chronologically) and then by pruefidentifikator.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        Tuples of (previous_format_version, subsequent_format_version, pruefidentifikator).
    """
    pruefis_by_format_version = _get_pruefis_by_format_version(db_path)
    sorted_format_versions = sorted(pruefis_by_format_version.keys())

    for i, prev_fv in enumerate(sorted_format_versions):
        for subseq_fv in sorted_format_versions[i + 1 :]:
            if prev_fv >= subseq_fv:
                continue
            common_pruefis = pruefis_by_format_version[prev_fv] & pruefis_by_format_version[subseq_fv]
            for pruefi in sorted(common_pruefis):
                yield (prev_fv, subseq_fv, pruefi)


_BATCH_SIZE = 100


def _process_single_comparison(
    session: Session,
    db_path: Path,
    prev_fv: EdifactFormatVersion,
    subseq_fv: EdifactFormatVersion,
    pruefi: str,
) -> int:
    """Process a single comparison and add results to session. Returns number of line comparisons."""
    comparison = compare_ahb_across_format_versions(
        db_path=db_path,
        previous_format_version=prev_fv,
        subsequent_format_version=subseq_fv,
        pruefidentifikator=pruefi,
    )

    # pylint: disable=no-member
    summary_row = AhbComparisonSummaryTable(
        pruefidentifikator=pruefi,
        previous_format_version=prev_fv.value,
        subsequent_format_version=subseq_fv.value,
        total_lines=comparison.summary.total_lines,
        unchanged_count=comparison.summary.unchanged_count,
        modified_count=comparison.summary.modified_count,
        added_count=comparison.summary.added_count,
        removed_count=comparison.summary.removed_count,
    )
    session.add(summary_row)

    line_count = 0
    for line_comp in comparison.line_comparisons:
        line_row = AhbLineComparisonTable(
            pruefidentifikator=pruefi,
            previous_format_version=prev_fv.value,
            subsequent_format_version=subseq_fv.value,
            id_path=line_comp.id_path,
            diff_type=line_comp.diff_type.value,
            previous_line_id=str(line_comp.previous_line.id) if line_comp.previous_line else None,
            subsequent_line_id=str(line_comp.subsequent_line.id) if line_comp.subsequent_line else None,
            changed_fields=",".join(line_comp.changed_fields) if line_comp.changed_fields else None,
        )
        session.add(line_row)
        line_count += 1

    return line_count


def populate_comparison_tables(db_path: Path, batch_size: int = _BATCH_SIZE) -> int:
    """
    Create comparison tables and populate them with comparisons for all format version pairs.

    This function compares all Prüfidentifikators across all pairs of format versions
    (not just neighbouring ones) and stores the results in the same database.

    Args:
        db_path: Path to the SQLite database file (will be modified in place).
        batch_size: Number of comparisons to process before committing (default: 100).

    Returns:
        Total number of comparisons performed.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    logger.info("Created comparison tables")

    total_comparisons = 0
    total_line_comparisons = 0

    def get_fv_pair(candidate: tuple[EdifactFormatVersion, EdifactFormatVersion, str]) -> tuple[str, str]:
        return (candidate[0].value, candidate[1].value)

    with Session(engine) as session:
        for (prev_fv_val, subseq_fv_val), candidates in groupby(
            get_all_comparison_candidates(db_path), key=get_fv_pair
        ):
            logger.info("Comparing %s -> %s", prev_fv_val, subseq_fv_val)

            for prev_fv, subseq_fv, pruefi in candidates:
                total_line_comparisons += _process_single_comparison(session, db_path, prev_fv, subseq_fv, pruefi)
                total_comparisons += 1

                if total_comparisons % batch_size == 0:
                    session.commit()
                    logger.debug("Committed batch at %d comparisons", total_comparisons)

        session.commit()
        logger.info("Committed %d comparisons with %d line comparisons", total_comparisons, total_line_comparisons)

    with engine.connect() as conn:
        conn.execute(text("VACUUM"))
    logger.info("Vacuumed database")

    engine.dispose()

    return total_comparisons
