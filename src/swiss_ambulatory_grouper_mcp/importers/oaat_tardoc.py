"""Copy TARDOC tables from a local OAAT-derived SQLite database."""
from __future__ import annotations

from pathlib import Path

from .sqlite_copy import copy_tables_with_destination_prefix


def import_tardoc(source_db: Path, output_db: Path) -> list[str]:
    """Copy TARDOC source tables into the output DB as TD_* tables."""
    return copy_tables_with_destination_prefix(source_db, output_db, "TD_")
