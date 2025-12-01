import os
import sys
from dataclasses import dataclass
from pathlib import Path

import py7zr
import pytest


@dataclass(frozen=True)
class FormatVersions:
    previous_formatversion: str = "FV2410"
    subsequent_formatversion: str = "FV2504"


@pytest.fixture
def formatversions() -> FormatVersions:
    return FormatVersions()


@pytest.fixture
def temp_excel_file(tmp_path: Path) -> Path:
    return tmp_path / "pruefid.xlsx"

_PATH_OF_ENCRYPTED_AHB_DB = Path(__file__).parent / "test_data"/ "ahb.db.encrypted.7z"
@pytest.fixture(scope="module")
def unencrypted_ahb_database(tmp_path:Path)->Path:
    assert _PATH_OF_ENCRYPTED_AHB_DB.exists()
    possible_path_of_unencrypted_db = _PATH_OF_ENCRYPTED_AHB_DB.with_stem("ahb.db") # w/o the 'encrypted'
    if possible_path_of_unencrypted_db.exists():
        return possible_path_of_unencrypted_db # because we assume the developer placed it there AND it's up to date
    decryption_key = os.environ.get("SQLITE_AHB_DB_7Z_ARCHIVE_PASSWORD")
    if not decryption_key:
        pytest.skip("Test cannot be run because DB cannot be decrypted. This should not happen in the CI on any Hochfrequenz repository")
        # as a human developer just download the latest DECRYPTED DB from the release artifacts here:
        # https://github.com/Hochfrequenz/xml-migs-and-ahbs/releases
        raise ValueError("This should not happen in the CI on any Hochfrequenz repository and not in PyTest")
    with py7zr.SevenZipFile(_PATH_OF_ENCRYPTED_AHB_DB, mode="r", password=decryption_key) as archive:
        archive.extractall(path=tmp_path)
    extracted_db_path = tmp_path / "ahb.db"
    assert extracted_db_path.exists(), f"Expected extracted database at {extracted_db_path}"
    return extracted_db_path
