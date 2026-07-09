"""External source inventory and requirement reporting."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable

from .config import PipelineConfig, build_config

OAAT_URL = "https://oaat-otma.ch/gesamt-tarifsystem/tarifkomponenten-und-software"
BFS_DE_URL = "https://www.bfs.admin.ch/bfs/de/home/statistiken/gesundheit/nomenklaturen/medkk/instrumente-medizinische-kodierung.html"
BFS_FR_URL = "https://www.bfs.admin.ch/bfs/fr/home/statistiques/sante/nomenclatures/medkk/instruments-codage-medical.html"
BFS_IT_URL = "https://www.bfs.admin.ch/bfs/it/home/statistiche/salute/nomenclature/medkk/strumenti-codifica-medica.html"


@dataclass(frozen=True)
class SourceRequirement:
    key: str
    label: str
    path: Path
    source_url: str
    notes: str


@dataclass(frozen=True)
class SourceStatus(SourceRequirement):
    present: bool = False
    size: int | None = None
    sha256: str | None = None


def source_requirements(config: PipelineConfig) -> list[SourceRequirement]:
    files = config.input_files
    return [
        SourceRequirement("lkaat_db", "OAAT LKAAT SQLite database with LK_* tables", files["lkaat_db"], OAAT_URL, "Obtain from OAAT tariff components/software; convert locally to SQLite if needed."),
        SourceRequirement("tardoc_db", "OAAT TARDOC SQLite database with TD_* tables", files["tardoc_db"], OAAT_URL, "Obtain from OAAT tariff components/software; convert locally to SQLite if needed."),
        SourceRequirement("ambp_file", "OAAT ambulatory flat-rate catalogue CSV", files["ambp_file"], OAAT_URL, "Place a local CSV export here; Capitulum is derived from this AmbP catalogue."),
        SourceRequirement("icd10_de_claml", "BFS ICD-10-GM ClaML DE", files["icd10_de_claml"], BFS_DE_URL, "Download from BFS medical coding instruments."),
        SourceRequirement("icd10_fr_claml", "BFS CIM-10-GM ClaML FR", files["icd10_fr_claml"], BFS_FR_URL, "Download from BFS instruments de codage médical."),
        SourceRequirement("icd10_it_claml", "BFS ICD-10-GM ClaML IT", files["icd10_it_claml"], BFS_IT_URL, "Download from BFS strumenti di codifica medica."),
    ]


def build_inventory(config: PipelineConfig) -> list[SourceStatus]:
    inventory: list[SourceStatus] = []
    for req in source_requirements(config):
        if req.path.exists():
            inventory.append(
                SourceStatus(
                    **req.__dict__,
                    present=True,
                    size=req.path.stat().st_size,
                    sha256=sha256_file(req.path),
                )
            )
        else:
            inventory.append(SourceStatus(**req.__dict__, present=False, size=None, sha256=None))
    return inventory


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def missing_sources(inventory: Iterable[SourceStatus]) -> list[SourceStatus]:
    return [item for item in inventory if not item.present]


def requirements_markdown(config: PipelineConfig) -> str:
    lines = [
        "# External data requirements",
        "",
        "This repository does not include official OAAT or BFS source files and does not include generated SQLite databases.",
        "Each user must obtain the required files independently and place them in the configured local data directory.",
        "",
        f"Configured local data directory: `{config.data_dir}`",
        f"Configured source directory: `{config.source_dir}`",
        f"Configured output directory: `{config.output_dir}`",
        f"Tariff year: `{config.year}`; ICD/CIM source year: `{config.icd_year}`",
        "",
        "## Required files",
        "",
    ]
    for req in source_requirements(config):
        lines.extend(
            [
                f"### {req.key}",
                f"- Label: {req.label}",
                f"- Expected local path: `{req.path}`",
                f"- Source: {req.source_url}",
                f"- Notes: {req.notes}",
                "",
            ]
        )
    lines.extend(
        [
            "## Source overview",
            "",
            f"Most tariff components are obtained from OAAT after registration: {OAAT_URL}",
            "ICD-10 / CIM-10 language versions are obtained from the Swiss Federal Statistical Office (BFS) coding instrument pages.",
        ]
    )
    return "\n".join(lines) + "\n"


def format_inventory(inventory: Iterable[SourceStatus]) -> str:
    lines = []
    for item in inventory:
        status = "OK" if item.present else "MISSING"
        lines.append(f"[{status}] {item.key}: {item.path}")
        if item.present:
            lines.append(f"       size={item.size} sha256={item.sha256}")
        else:
            lines.append(f"       source={item.source_url}")
            lines.append(f"       notes={item.notes}")
    return "\n".join(lines) + "\n"


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check local external OAAT/BFS source files.")
    parser.add_argument("--year", default=None)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--icd-year", default=None, help="Use ICD/CIM source files from this BFS year.")
    parser.add_argument("--requirements", action="store_true", help="Print Markdown requirements instead of status.")
    args = parser.parse_args(argv)
    config = build_config(
        year=args.year,
        data_dir=args.data_dir,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        icd_year=args.icd_year,
    )
    if args.requirements:
        print(requirements_markdown(config), end="")
        return 0
    inventory = build_inventory(config)
    print(format_inventory(inventory), end="")
    return 1 if missing_sources(inventory) else 0


if __name__ == "__main__":
    raise SystemExit(cli())
