"""Derive Capitulum/chapter data from the OAAT AmbP catalogue."""
from __future__ import annotations

from pathlib import Path
import sqlite3

from .tabular import read_csv_rows


def import_capitulum(ambp_file: Path, output_db: Path) -> int:
    """Create ``Capitulum`` from AmbP catalogue rows with ``Cap...`` codes."""
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
