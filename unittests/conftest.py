from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class FormatVersions:
    """
    provides example formatversions.
    """

    previous_formatversion: str = "FV2410"
    subsequent_formatversion: str = "FV2504"


@pytest.fixture
def formatversions() -> FormatVersions:
    return FormatVersions()
