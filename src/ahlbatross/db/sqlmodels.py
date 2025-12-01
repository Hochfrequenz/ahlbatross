"""SQLModel tables for storing AHB comparisons."""

from typing import Optional

from sqlmodel import Field, Index, SQLModel


class AhbLineComparisonTable(SQLModel, table=True):
    """
    Stores comparison results for individual AHB lines across format versions.
    References lines from v_ahbtabellen by their id.
    """

    __tablename__ = "ahb_line_comparison"
    __table_args__ = (
        Index("ix_line_comp_versions", "previous_format_version", "subsequent_format_version"),
        Index(
            "ix_line_comp_pruefi_versions", "pruefidentifikator", "previous_format_version", "subsequent_format_version"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    pruefidentifikator: str = Field(index=True)
    previous_format_version: str = Field(index=True)
    subsequent_format_version: str = Field(index=True)
    id_path: str = Field(index=True)
    diff_type: str = Field(index=True)
    previous_line_id: Optional[str] = Field(
        default=None, description="ID of the line in v_ahbtabellen from previous version"
    )
    subsequent_line_id: Optional[str] = Field(
        default=None, description="ID of the line in v_ahbtabellen from subsequent version"
    )
    changed_fields: Optional[str] = Field(default=None, description="Comma-separated list of changed field names")


class AhbComparisonSummaryTable(SQLModel, table=True):
    """
    Stores summary statistics for AHB comparisons.
    """

    __tablename__ = "ahb_comparison_summary"
    __table_args__ = (
        Index("ix_summary_versions", "previous_format_version", "subsequent_format_version"),
        Index(
            "ix_summary_pruefi_versions", "pruefidentifikator", "previous_format_version", "subsequent_format_version"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    pruefidentifikator: str = Field(index=True)
    previous_format_version: str = Field(index=True)
    subsequent_format_version: str = Field(index=True)
    total_lines: int
    unchanged_count: int
    modified_count: int
    added_count: int
    removed_count: int
