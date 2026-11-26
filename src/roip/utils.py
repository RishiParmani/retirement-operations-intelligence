"""Small shared helpers (logging)."""
from __future__ import annotations
import logging
import sys
from pathlib import Path


def get_logger(name: str = "roip", log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Console logger, optionally mirrored to a file. Safe to call repeatedly."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%H:%M:%S")
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(fmt)
        logger.addHandler(h)
    if log_file is not None and not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger
