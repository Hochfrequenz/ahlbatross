"""
Models for comparing AHBs between two format versions.
"""

from efoli import EdifactFormatVersion
from fundamend.sqlmodels import AhbTabellenLine
from pydantic import BaseModel, Field

from ahlbatross.enums.diff_types import DiffType


class AhbLineComparison(BaseModel):
    """
    Comparison of a single AHB line across two format versions.
    Uses id_path as the stable key for matching lines.
    """

    id_path: str = Field(description="The stable identifier path that links lines across format versions.")
    diff_type: DiffType = Field(description="Type of change: UNCHANGED, MODIFIED, ADDED, or REMOVED.")
    previous_line: AhbTabellenLine | None = Field(
        default=None, description="The line from the previous format version (None if ADDED)."
    )
    subsequent_line: AhbTabellenLine | None = Field(
        default=None, description="The line from the subsequent format version (None if REMOVED)."
    )
    changed_fields: list[str] = Field(
        default_factory=list,
        description="List of field names that changed between versions (only populated for MODIFIED).",
    )

    model_config = {"arbitrary_types_allowed": True}


class AhbComparisonSummary(BaseModel):
    """Summary statistics for an AHB comparison."""

    total_lines: int = Field(description="Total number of unique lines across both versions.")
    unchanged_count: int = Field(description="Number of lines that are identical in both versions.")
    modified_count: int = Field(description="Number of lines that were modified between versions.")
    added_count: int = Field(description="Number of lines added in the subsequent version.")
    removed_count: int = Field(description="Number of lines removed from the previous version.")


class AhbComparison(BaseModel):
    """
    Comprehensive comparison of an AHB (Prüfidentifikator) across two format versions.
    Contains all lines from both versions, matched by id_path, with their diff status.
    """

    pruefidentifikator: str = Field(description="The Prüfidentifikator being compared.")
    previous_format_version: EdifactFormatVersion = Field(description="The earlier format version.")
    subsequent_format_version: EdifactFormatVersion = Field(description="The later format version.")
    summary: AhbComparisonSummary = Field(description="Summary statistics of the comparison.")
    line_comparisons: list[AhbLineComparison] = Field(description="List of all line comparisons, sorted by sort_path.")

    model_config = {"arbitrary_types_allowed": True}
