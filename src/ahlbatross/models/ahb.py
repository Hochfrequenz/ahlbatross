"""
Classes that are used to compare AHBs between two formatversions row by row and assemble the output table.
"""

from typing import List

from pydantic import BaseModel, Field

from ahlbatross.enums.diff_types import DiffType
from fundamend.sqlmodels import AhbTabellenLine

class AhbRowDiff(BaseModel):
    """
    Differences between two formatversions for identical pruefIDs within one row.
    """

    diff_type: DiffType = Field(
        default=DiffType.UNCHANGED, description="Type of difference between two formatversions within a single row."
    )
    changed_entries: List[str] = Field(
        default_factory=list,
        description="List of entries (single cells) that changed between two formatversions within a single row.",
    )


class AhbRowComparison(BaseModel):
    """
    Output table assembly (a separate "row numbering" column is added directly in the CSV/XLSX export functions).
    """

    previous_formatversion: AhbTabellenLine
    diff: AhbRowDiff
    subsequent_formatversion: AhbTabellenLine

    @property
    def key(self) -> str:
        """
        Returns the business key for a given AhbRowComparison (previous_FV key should be equivalent to subsequent_FV).
        """
        return self.previous_formatversion.id_path
