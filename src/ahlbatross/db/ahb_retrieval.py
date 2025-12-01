"""Retrieve AHB data from SQLite database."""

from pathlib import Path

from efoli import EdifactFormatVersion
from fundamend.sqlmodels import AhbTabellenLine
from sqlmodel import Session, create_engine, select


def get_anwendungsfall_from_db(
    db_path: Path,
    edifact_format_version: EdifactFormatVersion,
    pruefidentifikator: str,
) -> list[AhbTabellenLine]:
    """
    Retrieve AHB lines from the SQLite database view v_ahbtabellen.

    Args:
        db_path: Path to the SQLite database file.
        edifact_format_version: The EDIFACT format version to filter by.
        pruefidentifikator: The Prüfidentifikator to filter by.

    Returns:
        List of AhbTabellenLine from the view.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        statement = (
            select(AhbTabellenLine)
            .where(
                AhbTabellenLine.format_version == edifact_format_version,
                AhbTabellenLine.pruefidentifikator == pruefidentifikator,
            )
            .order_by(AhbTabellenLine.sort_path)
        )
        return list(session.exec(statement).all())
