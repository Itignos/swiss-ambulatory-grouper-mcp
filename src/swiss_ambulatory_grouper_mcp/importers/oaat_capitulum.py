"""Import or derive Capitulum/chapter data into SQLite."""
from __future__ import annotations

from pathlib import Path
import sqlite3

from .sqlite_copy import quote_identifier
from .tabular import import_tabular_file, read_csv_rows


def import_capitulum(source_file: Path, output_db: Path, *, fallback_ambp_file: Path | None = None) -> int:
    """Import Capitulum from CSV or derive a minimal table from AmbP CSV.

    A separate Capitulum source is preferable. If it is not available, OAAT AmbP
    catalogue rows with codes such as ``Cap00`` are enough to expose a basic
    chapter table without shipping another source file.
    """
    if source_file.exists():
        return import_tabular_file(source_file, output_db, "Capitulum")
    if fallback_ambp_file is None or not fallback_ambp_file.exists():
        raise FileNotFoundError(
            f"Missing Capitulum source: {source_file}. Provide capitulum.csv or an AmbP CSV fallback."
        )
    return derive_capitulum_from_ambp(fallback_ambp_file, output_db)


def derive_capitulum_from_ambp(ambp_file: Path, output_db: Path) -> int:
    headers, rows = read_csv_rows(ambp_file)
    lower_headers = [header.lower() for header in headers]
    index = {name: lower_headers.index(name) for name in lower_headers}

    def value(row: list[str], column: str) -> str:
        pos = index.get(column)
        return row[pos].strip() if pos is not None and pos < len(row) else ""

    chapter_rows: list[tuple[str, str, str, str, str]] = []
    seen: set[str] = set()
    for row in rows:
        code = value(row, "code")
        if not code.startswith("Cap") or code in seen:
            continue
        seen.add(code)
        chapter_rows.append(
            (
                code,
                value(row, "title_de"),
                value(row, "title_fr"),
                value(row, "title_it"),
                value(row, "version"),
            )
        )

    output_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_db) as conn:
        conn.execute("DROP TABLE IF EXISTS Capitulum")
        conn.execute(
            """
            CREATE TABLE Capitulum (
                code TEXT PRIMARY KEY,
                title_de TEXT,
                title_fr TEXT,
                title_it TEXT,
                version TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO Capitulum (code, title_de, title_fr, title_it, version) VALUES (?, ?, ?, ?, ?)",
            chapter_rows,
        )
        conn.commit()
    return len(chapter_rows)
