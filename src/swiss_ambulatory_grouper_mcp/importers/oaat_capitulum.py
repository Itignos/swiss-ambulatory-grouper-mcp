"""Import Capitulum/chapter data into SQLite."""
from __future__ import annotations

from pathlib import Path

from .tabular import import_tabular_file


def import_capitulum(source_file: Path, output_db: Path) -> int:
    return import_tabular_file(source_file, output_db, "Capitulum")
