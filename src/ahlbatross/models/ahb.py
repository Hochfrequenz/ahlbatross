"""
Classes that are used to compare AHBs between two formatversions row by row and assemble the output table.
"""

from typing import List

from kohlrahbi.models.anwendungshandbuch import AhbLine
from pydantic import BaseModel, Field

from ahlbatross.enums.diff_types import DiffType


class AhbRow(AhbLine):
    """
    Represents a single row of AHB properties according to scraped machine-readable-AHBs provided by kohlr_AHB_i.
    (1) segment_name == "Segmentname" (e.g. "Nachrichten-Kopfsegment")
    (2) segment_group_key == "Segmentgruppe" (e.g "SG2")
    (3) segment_code == "Segment" (e.g. "UNH")
    (4) data_element == "Datenelement" (e.g. "0062")
    (5) segment_id == "Segment ID" (e.g. "00001")
    (6a) value_pool_entry == "Code" (e.g. "E_6022")
    (6b) value_pool_entry == "Qualifier" (e.g. "IC")
    (7) name == "Beschreibung" (e.g. "Informationskontakt")
    (8) ahb_expression == "Bedingungsausdruck" (e.g. "Muss")
    (9) conditions == "Bedingung" (e.g. "[2] Wenn SG7 STS+Z06+Z10+ZC1 vorhanden.")
    """

    format_version: str = Field(..., description="Formatversion of an AHB (suffix for properties (1)-(9)).")


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
    Output table assembly.
    """

    index: int = Field(description="Indexing through rows according to segment appearances in the original AHB.", ge=0)
    previous_formatversion: AhbRow
    diff: AhbRowDiff
    subsequent_formatversion: AhbRow
