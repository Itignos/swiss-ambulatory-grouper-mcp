"""Copy TARDOC TD_* tables from a local OAAT-derived SQLite database."""
from __future__ import annotations

from pathlib import Path

from .sqlite_copy import copy_tables_with_prefix


def import_tardoc(source_db: Path, output_db: Path) -> list[str]:
    return copy_tables_with_prefix(source_db, output_db, "TD_")
