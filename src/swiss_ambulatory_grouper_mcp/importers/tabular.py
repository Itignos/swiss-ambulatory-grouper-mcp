"""Small CSV/XLSX import helpers for OAAT-like tabular files."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable

from .sqlite_copy import quote_identifier, require_file


def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
        return dialect.delimiter
    except csv.Error:
        return ";" if ";" in sample else ","


def read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    delimiter = sniff_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV file is empty: {path}")
    headers = [header.strip() or f"column_{index + 1}" for index, header in enumerate(rows[0])]
    return headers, rows[1:]


def import_tabular_file(path: Path, db_path: Path, table_name: str) -> int:
    """Import a CSV file into ``table_name`` using TEXT columns.

    XLSX can be added by installing the optional ``excel`` extra; for the first
    public version CSV is the stable, dependency-free interchange format.
    """

    require_file(path, table_name)
    if path.suffix.lower() not in {".csv", ".tsv"}:
        raise ValueError(
            f"Unsupported tabular file format for {table_name}: {path.suffix}. "
            "Convert the official source to CSV first or add an importer."
        )
    headers, rows = read_csv_rows(path)
    if path.suffix.lower() == ".tsv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            all_rows = list(reader)
        headers = [header.strip() or f"column_{index + 1}" for index, header in enumerate(all_rows[0])]
        rows = all_rows[1:]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    q_table = quote_identifier(table_name)
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"DROP TABLE IF EXISTS {q_table}")
        column_sql = ", ".join(f"{quote_identifier(column)} TEXT" for column in headers)
        conn.execute(f"CREATE TABLE {q_table} ({column_sql})")
        if rows:
            placeholders = ", ".join("?" for _ in headers)
            normalized_rows = [normalize_row(row, len(headers)) for row in rows if any(cell.strip() for cell in row)]
            conn.executemany(f"INSERT INTO {q_table} VALUES ({placeholders})", normalized_rows)
        conn.commit()
    return len([row for row in rows if any(cell.strip() for cell in row)])


def normalize_row(row: Iterable[str], width: int) -> list[str]:
    values = list(row)
    if len(values) < width:
        values.extend([""] * (width - len(values)))
    return values[:width]
