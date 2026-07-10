"""Runtime configuration for the local TarifMatcher MCP container."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class TarifMatcherRuntimeConfig:
    """Configuration for the Java TarifMatcher bridge and MCP runtime."""

    jar_path: Path
    data_dir: Path
    sqlite_db: Path | None
    base_url: str
    tariff_year: str
    icd_year: str

    @classmethod
    def from_env(cls) -> "TarifMatcherRuntimeConfig":
        return cls(
            jar_path=Path(os.environ.get("TARIFMATCHER_JAR", "/data/runtime/tarifmatcher/current/tarifmatcher-standalone.jar")).expanduser(),
            data_dir=Path(os.environ.get("TARIFMATCHER_DATA_DIR", "/data/runtime/tarifmatcher/current")).expanduser(),
            sqlite_db=Path(os.environ["SWISS_AMBULATORY_GROUPER_DB"]).expanduser()
            if os.environ.get("SWISS_AMBULATORY_GROUPER_DB")
            else None,
            base_url=os.environ.get("TARIFMATCHER_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
            tariff_year=os.environ.get("TARIFMATCHER_TARIFF_YEAR", os.environ.get("SWISS_AMBULATORY_GROUPER_YEAR", "2027")),
            icd_year=os.environ.get("TARIFMATCHER_ICD_YEAR", os.environ.get("SWISS_AMBULATORY_GROUPER_ICD_YEAR", "2026")),
        )

    def validate_files(self) -> dict[str, dict[str, object]]:
        def status(path: Path | None, *, kind: str) -> dict[str, object]:
            if path is None:
                return {"path": None, "present": False, "kind": kind}
            return {
                "path": str(path),
                "present": path.exists(),
                "kind": kind,
                "is_file": path.is_file() if path.exists() else False,
                "is_dir": path.is_dir() if path.exists() else False,
            }

        return {
            "jar": status(self.jar_path, kind="file"),
            "data_dir": status(self.data_dir, kind="directory"),
            "sqlite_db": status(self.sqlite_db, kind="file"),
        }
