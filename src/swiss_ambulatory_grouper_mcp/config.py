"""Central configuration for local Swiss ambulatory tariff imports.

The public repository intentionally contains no official OAAT/BFS source data
and no generated SQLite database.  All data paths point to a local workspace
outside the Git repository.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping, Sequence


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
DEFAULT_DATA_DIR = REPO_ROOT.parent / "_external_data" / REPO_ROOT.name
DEFAULT_YEAR = os.environ.get("SWISS_AMBULATORY_GROUPER_YEAR", "2027")


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for one local import build."""

    year: str
    repo_root: Path
    data_dir: Path
    source_dir: Path
    work_dir: Path
    output_db: Path
    input_files: Mapping[str, Path]
    pipeline_steps: Sequence[str]


def build_config(year: str | None = None, data_dir: str | Path | None = None) -> PipelineConfig:
    """Build the central pipeline config.

    Priority for the external data workspace:
    1. explicit ``data_dir`` argument
    2. ``SWISS_AMBULATORY_GROUPER_DATA_DIR`` environment variable
    3. sibling ``_external_data/<repo-name>`` next to the repository
    """

    selected_year = str(year or DEFAULT_YEAR)
    selected_data_dir = Path(
        data_dir
        or os.environ.get("SWISS_AMBULATORY_GROUPER_DATA_DIR")
        or DEFAULT_DATA_DIR
    ).expanduser()

    source_dir = selected_data_dir / "sources"
    work_dir = selected_data_dir / "work"
    output_db = selected_data_dir / "output" / f"swiss_ambulatory_{selected_year}.sqlite"

    input_files: dict[str, Path] = {
        "lkaat_db": source_dir / "oaat" / selected_year / "lkaat" / "lkaat.sqlite",
        "tardoc_db": source_dir / "oaat" / selected_year / "tardoc" / "tardoc.sqlite",
        "ambp_file": source_dir / "oaat" / selected_year / "ambp" / "ambp.csv",
        "capitulum_file": source_dir / "oaat" / selected_year / "capitulum" / "capitulum.csv",
        "icd10_de_claml": source_dir / "bfs" / selected_year / "icd10" / "de" / "icd10_de_claml.xml",
        "icd10_fr_claml": source_dir / "bfs" / selected_year / "icd10" / "fr" / "icd10_fr_claml.xml",
        "icd10_it_claml": source_dir / "bfs" / selected_year / "icd10" / "it" / "icd10_it_claml.xml",
    }

    return PipelineConfig(
        year=selected_year,
        repo_root=REPO_ROOT,
        data_dir=selected_data_dir,
        source_dir=source_dir,
        work_dir=work_dir,
        output_db=output_db,
        input_files=input_files,
        pipeline_steps=(
            "validate_sources",
            "import_lkaat",
            "import_tardoc",
            "import_ambp",
            "import_capitulum",
            "import_icd10",
            "analyze",
        ),
    )


CONFIG = build_config()
