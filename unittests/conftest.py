import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager

import py7zr
import pytest
from sqlalchemy.engine import Engine
from sqlmodel import create_engine

_PATH_OF_ENCRYPTED_AHB_DB = Path(__file__).parent / "test_data" / "ahb.db.encrypted.7z"
_PATH_OF_UNENCRYPTED_AHB_DB_7Z = Path(__file__).parent / "test_data" / "ahb.db.7z"
_PATH_OF_UNENCRYPTED_AHB_DB = Path(__file__).parent / "test_data" / "ahb.db"


@contextmanager
def _create_disposed_engine(db_path: Path) -> Iterator[Engine]:
    """Create an engine that is properly disposed after use."""
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def create_disposed_engine() -> Callable[[Path], ContextManager[Engine]]:
    """Fixture that provides a context manager for creating engines that auto-dispose."""
    return _create_disposed_engine


@pytest.fixture
def unencrypted_ahb_database(tmp_path: Path) -> Path:
    # Option 1: Developer placed the raw .db file directly
    if _PATH_OF_UNENCRYPTED_AHB_DB.exists():
        return _PATH_OF_UNENCRYPTED_AHB_DB
    # Option 2: Unencrypted 7z archive exists (no password needed)
    if _PATH_OF_UNENCRYPTED_AHB_DB_7Z.exists():
        with py7zr.SevenZipFile(_PATH_OF_UNENCRYPTED_AHB_DB_7Z, mode="r") as archive:
            archive.extractall(path=tmp_path)
        extracted_db_path = tmp_path / "ahb.db"
        assert extracted_db_path.exists(), f"Expected extracted database at {extracted_db_path}"
        return extracted_db_path
    # Option 3: Encrypted 7z archive (password required)
    assert _PATH_OF_ENCRYPTED_AHB_DB.exists(), f"No AHB database found at {_PATH_OF_ENCRYPTED_AHB_DB}"
    decryption_key = os.environ.get("SQLITE_AHB_DB_7Z_ARCHIVE_PASSWORD")
    if not decryption_key:
        pytest.skip(
            "Test cannot be run because DB cannot be decrypted. "
            "This should not happen in the CI on any Hochfrequenz repository"
        )
        # as a human developer just download the latest DECRYPTED DB from the release artifacts here:
        # https://github.com/Hochfrequenz/xml-migs-and-ahbs/releases
        raise ValueError("This should not happen in the CI on any Hochfrequenz repository and not in PyTest")
    with py7zr.SevenZipFile(_PATH_OF_ENCRYPTED_AHB_DB, mode="r", password=decryption_key) as archive:
        archive.extractall(path=tmp_path)
    extracted_db_path = tmp_path / "ahb.db"
    assert extracted_db_path.exists(), f"Expected extracted database at {extracted_db_path}"
    return extracted_db_path
