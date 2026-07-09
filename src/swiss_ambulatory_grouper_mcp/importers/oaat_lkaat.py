"""Copy LKAAT tables from a local OAAT-derived SQLite database."""
from __future__ import annotations

from pathlib import Path

from .sqlite_copy import copy_tables_with_destination_prefix


def import_lkaat(source_db: Path, output_db: Path) -> list[str]:
    """Copy LKAAT source tables into the output DB as LK_* tables."""
    return copy_tables_with_destination_prefix(source_db, output_db, "LK_")
