"""
logger instance for ahlbatross.
"""

import logging.config
from pathlib import Path

logger_config_file: Path = Path(__file__).with_suffix(".ini")

logging.config.fileConfig(logger_config_file)
logger = logging.getLogger("ahlbatross")
