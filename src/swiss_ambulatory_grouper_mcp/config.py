"""Central configuration for local Swiss ambulatory tariff imports.

The public repository intentionally contains no official OAAT/BFS source data
and no generated SQLite database. All data paths point to local workspaces
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
DEFAULT_SOURCE_DIR = DEFAULT_DATA_DIR / "sources"
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "output"
DEFAULT_YEAR = os.environ.get("SWISS_AMBULATORY_GROUPER_YEAR", "2027")
# Optional: use ICD/CIM source files from a different BFS year than the tariff year.
# Example: build tariff 2027 with BFS ICD/CIM 2026 while no BFS 2027 ClaML files exist yet.
DEFAULT_ICD_YEAR = os.environ.get("SWISS_AMBULATORY_GROUPER_ICD_YEAR")


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for one local import build."""

    year: str
    icd_year: str
    repo_root: Path
    data_dir: Path
    source_dir: Path
    work_dir: Path
    output_dir: Path
    output_db: Path
    input_files: Mapping[str, Path]
    pipeline_steps: Sequence[str]


def build_config(
    year: str | None = None,
    data_dir: str | Path | None = None,
    source_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    icd_year: str | None = None,
) -> PipelineConfig:
    """Build the central pipeline config.

    Priority for paths:
    1. explicit function/CLI arguments
    2. environment variables
       - ``SWISS_AMBULATORY_GROUPER_DATA_DIR``
       - ``SWISS_AMBULATORY_GROUPER_SOURCE_DIR``
       - ``SWISS_AMBULATORY_GROUPER_OUTPUT_DIR``
    3. sibling ``_external_data/<repo-name>`` next to the repository
    """

    selected_year = str(year or DEFAULT_YEAR)
    selected_icd_year = str(icd_year or DEFAULT_ICD_YEAR or selected_year)
    selected_data_dir = Path(
        data_dir
        or os.environ.get("SWISS_AMBULATORY_GROUPER_DATA_DIR")
        or DEFAULT_DATA_DIR
    ).expanduser()
    selected_source_dir = Path(
        source_dir
        or os.environ.get("SWISS_AMBULATORY_GROUPER_SOURCE_DIR")
        or selected_data_dir / "sources"
    ).expanduser()
    selected_output_dir = Path(
        output_dir
        or os.environ.get("SWISS_AMBULATORY_GROUPER_OUTPUT_DIR")
        or selected_data_dir / "output"
    ).expanduser()

    input_files = build_input_files(selected_source_dir, selected_year, selected_icd_year)

    return PipelineConfig(
        year=selected_year,
        icd_year=selected_icd_year,
        repo_root=REPO_ROOT,
        data_dir=selected_data_dir,
        source_dir=selected_source_dir,
        work_dir=selected_data_dir / "work",
        output_dir=selected_output_dir,
        output_db=selected_output_dir / f"swiss_ambulatory_{selected_year}.sqlite",
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


def build_input_files(source_dir: Path, year: str, icd_year: str) -> dict[str, Path]:
    """Return expected source files for a catalogue/application year."""

    oaat_year_dir = source_dir / "oaat" / year
    bfs_year_dir = source_dir / "bfs" / icd_year

    oaat_by_year: dict[str, dict[str, Path]] = {
        "2026": {
            "lkaat_db": oaat_year_dir / "LKAAT_v1.0c_260402_Leistungskatalog_ambulante_Arzttarife.db",
            "tardoc_db": oaat_year_dir / "Anhang_A2_Katalog_des_TARDOC_1.4c_251128_2.db",
            "ambp_file": oaat_year_dir / "250808_Anhang_A1_Katalog_der_Ambulanten_Pauschalen_CSV_v1.1c.csv",
        },
        "2027": {
            "lkaat_db": oaat_year_dir / "Leistungskatalog_ambulante_Arzttarife__LKAAT__1.1.db",
            "tardoc_db": oaat_year_dir / "Anhang_A2_TARDOC_1.5.db",
            "ambp_file": oaat_year_dir / "Anhang_A1_Katalog_der_Ambulanten_Pauschalen_1.2.csv",
        },
    }
    icd_by_year: dict[str, dict[str, Path]] = {
        "2026": {
            "icd10_de_claml": bfs_year_dir / "icd10gm2026syst-claml" / "Klassifikationsdateien" / "icd10gm2026syst_claml_20250912.xml",
            "icd10_fr_claml": bfs_year_dir / "dz-f-14.04.01-cim10-gm-2024-02-ClaML-SI" / "CIM10GM2024_ClaML_S_FR_20241031.xml",
            "icd10_it_claml": bfs_year_dir / "dz-i-14.04.01-cim10-gm-2024-02-ClaML-SI" / "ICD10GM2024_ClaML_S_IT_20241031.xml",
        },
        "2027": {
            "icd10_de_claml": bfs_year_dir / "icd10gm2027syst-claml" / "Klassifikationsdateien" / "icd10gm2027syst_claml.xml",
            "icd10_fr_claml": bfs_year_dir / "cim10gm2027-claml-fr" / "CIM10GM2027_ClaML_S_FR.xml",
            "icd10_it_claml": bfs_year_dir / "icd10gm2027-claml-it" / "ICD10GM2027_ClaML_S_IT.xml",
        },
    }

    inputs = oaat_by_year.get(
        year,
        {
            "lkaat_db": oaat_year_dir / "lkaat.sqlite",
            "tardoc_db": oaat_year_dir / "tardoc.sqlite",
            "ambp_file": oaat_year_dir / "ambp.csv",
        },
    ).copy()
    inputs.update(
        icd_by_year.get(
            icd_year,
            {
                "icd10_de_claml": bfs_year_dir / "icd10" / "de" / "icd10_de_claml.xml",
                "icd10_fr_claml": bfs_year_dir / "icd10" / "fr" / "icd10_fr_claml.xml",
                "icd10_it_claml": bfs_year_dir / "icd10" / "it" / "icd10_it_claml.xml",
            },
        )
    )
    return inputs


CONFIG = build_config()
