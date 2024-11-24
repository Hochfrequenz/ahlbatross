"""
Possible types of differences between individual AhbRow's of two formatversions.
"""

from enum import StrEnum


class DiffType(StrEnum):
    """
    Types of differences between segments of two formatversions.
    """

    UNCHANGED = ""
    MODIFIED = "ÄNDERUNG"
    REMOVED = "ENTFÄLLT"
    ADDED = "NEU"
