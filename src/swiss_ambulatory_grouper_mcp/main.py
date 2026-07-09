"""Build the local Swiss ambulatory tariff SQLite database."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sqlite3
from pathlib import Path

from .config import PipelineConfig, build_config
from .importers.bfs_icd10 import create_compatibility_views, import_icd10_claml
from .importers.oaat_ambp import import_ambp
from .importers.oaat_capitulum import import_capitulum
from .importers.oaat_lkaat import import_lkaat
from .importers.oaat_tardoc import import_tardoc
from .importers.sqlite_copy import require_file, summarize_db
from .source_inventory import build_inventory, format_inventory, missing_sources


def validate_sources(config: PipelineConfig) -> None:
    inventory = build_inventory(config)
    missing = missing_sources(inventory)
    if missing:
        raise FileNotFoundError(
            "Missing required external source files:\n"
            + format_inventory(missing)
            + "\nRun scripts/print_source_requirements.py for official source URLs."
        )


def ensure_metadata(output_db: Path, config: PipelineConfig) -> None:
    with sqlite3.connect(output_db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS import_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        metadata = {
            "year": config.year,
            "icd_year": config.icd_year,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_dir": str(config.data_dir),
            "source_dir": str(config.source_dir),
            "output_dir": str(config.output_dir),
        }
        conn.executemany(
            "INSERT OR REPLACE INTO import_metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        conn.commit()


def build_database(config: PipelineConfig, *, force: bool = False) -> dict[str, object]:
    validate_sources(config)
    if config.output_db.exists():
        if not force:
            raise FileExistsError(f"Output database already exists. Use --force to overwrite: {config.output_db}")
        config.output_db.unlink()
    config.output_db.parent.mkdir(parents=True, exist_ok=True)

    files = config.input_files
    print(f"Building SQLite database for {config.year}: {config.output_db}")

    print("Importing LKAAT LK_* tables...")
    lkaat_tables = import_lkaat(files["lkaat_db"], config.output_db)
    print(f"  copied {len(lkaat_tables)} LK_* table(s)")

    print("Importing TARDOC TD_* tables...")
    tardoc_tables = import_tardoc(files["tardoc_db"], config.output_db)
    print(f"  copied {len(tardoc_tables)} TD_* table(s)")

    print("Importing AmbP...")
    ambp_rows = import_ambp(files["ambp_file"], config.output_db)
    print(f"  imported {ambp_rows} row(s)")

    print("Importing Capitulum from AmbP chapter rows...")
    capitulum_rows = import_capitulum(files["ambp_file"], config.output_db)
    print(f"  imported {capitulum_rows} row(s)")

    print("Importing ICD-10/CIM-10 ClaML DE/FR/IT...")
    icd_rows = {
        "de": import_icd10_claml(files["icd10_de_claml"], config.output_db, language="de"),
        "fr": import_icd10_claml(files["icd10_fr_claml"], config.output_db, language="fr"),
        "it": import_icd10_claml(files["icd10_it_claml"], config.output_db, language="it"),
    }
    create_compatibility_views(config.output_db)
    print(f"  imported ICD rows: {icd_rows}")

    ensure_metadata(config.output_db, config)
    with sqlite3.connect(config.output_db) as conn:
        conn.execute("ANALYZE")
        conn.commit()

    summary = summarize_db(config.output_db)
    print(f"Done. Summary: {summary}")
    return summary


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local SQLite DB from official local OAAT/BFS sources.")
    parser.add_argument("--year", default=None)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--icd-year", default=None, help="Use ICD/CIM source files from this BFS year, e.g. 2026 for a 2027 tariff build.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output SQLite database.")
    args = parser.parse_args(argv)
    config = build_config(
        year=args.year,
        data_dir=args.data_dir,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        icd_year=args.icd_year,
    )
    build_database(config, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
