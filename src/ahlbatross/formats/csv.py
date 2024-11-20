"""
functions for reading and writing csv files.
"""

from pathlib import Path

import pandas as pd
from pandas import DataFrame


def load_csv_dataframes(previous_ahb_path: Path, subsequent_ahb_path: Path) -> tuple[DataFrame, DataFrame]:
    """
    read csv input files.
    """
    previous_ahb: DataFrame = pd.read_csv(previous_ahb_path, dtype=str)
    subsequent_ahb: DataFrame = pd.read_csv(subsequent_ahb_path, dtype=str)
    return previous_ahb, subsequent_ahb


def get_csv_files(csv_dir: Path) -> list[Path]:
    """
    find and return all <pruefid>.csv files in a given directory.
    """
    if not csv_dir.exists():
        return []
    return sorted(csv_dir.glob("*.csv"))
