"""SQLite table copy helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def require_file(path: Path, label: str | None = None) -> None:
    if not path.exists():
        name = label or str(path)
        raise FileNotFoundError(f"Missing required source for {name}: {path}")


def list_tables(db_path: Path) -> list[str]:
    require_file(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


def copy_selected_tables(source_db: Path, destination_db: Path, mapping: dict[str, str]) -> list[str]:
    require_file(source_db, "SQLite source database")
    destination_db.parent.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    with sqlite3.connect(destination_db) as conn:
        source_alias = "src"
        q_alias = quote_identifier(source_alias)
        conn.execute(f"ATTACH DATABASE ? AS {q_alias}", (str(source_db),))
        try:
            for source_table, destination_table in mapping.items():
                q_source = quote_identifier(source_table)
                q_destination = quote_identifier(destination_table)
                conn.execute(f"DROP TABLE IF EXISTS main.{q_destination}")
                conn.execute(
                    f"CREATE TABLE main.{q_destination} AS SELECT * FROM {q_alias}.{q_source}"
                )
                copied.append(destination_table)
            conn.commit()
        finally:
            conn.execute(f"DETACH DATABASE {q_alias}")
    return copied


def copy_tables_with_prefix(source_db: Path, destination_db: Path, prefix: str) -> list[str]:
    matching = [table for table in list_tables(source_db) if table.startswith(prefix)]
    return copy_selected_tables(source_db, destination_db, {table: table for table in matching})


def summarize_db(db_path: Path) -> dict[str, object]:
    require_file(db_path, "SQLite output database")
    with sqlite3.connect(db_path) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        rows = {
            table: conn.execute(f"SELECT COUNT(*) FROM {quote_identifier(table)}").fetchone()[0]
            for table in tables
        }
    return {"table_count": len(tables), "rows": rows}
