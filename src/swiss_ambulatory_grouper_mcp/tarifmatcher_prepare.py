"""Prepare local non-git TarifMatcher runtime files from official OAAT ZIP archives."""
from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile


TARIFMATCHER_ZIPS = {
    "2026": "tarifmatcher-1.1.0.zip",
    "2027": "tarifmatcher-1.2.0.zip",
}


def prepare_tarifmatcher_runtime(
    *,
    source_dir: Path,
    output_dir: Path,
    years: list[str] | None = None,
    force: bool = True,
) -> dict[str, dict[str, str]]:
    """Extract official TarifMatcher ZIPs into output/runtime/tarifmatcher/<year>.

    The ZIP files remain outside the public repository. The extracted runtime is
    intended to be mounted into Docker/Kubernetes containers as private data.
    """
    selected_years = years or sorted(TARIFMATCHER_ZIPS)
    summary: dict[str, dict[str, str]] = {}
    for year in selected_years:
        if year not in TARIFMATCHER_ZIPS:
            supported = ", ".join(sorted(TARIFMATCHER_ZIPS))
            raise ValueError(f"Unsupported TarifMatcher year {year!r}. Supported years: {supported}")
        zip_path = source_dir / "oaat" / year / TARIFMATCHER_ZIPS[year]
        if not zip_path.exists():
            raise FileNotFoundError(f"Missing TarifMatcher ZIP for {year}: {zip_path}")
        destination = output_dir / "runtime" / "tarifmatcher" / year
        destination.mkdir(parents=True, exist_ok=True)
        with ZipFile(zip_path) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                target = destination / Path(member.filename).name
                if target.exists() and not force:
                    continue
                with zf.open(member) as src, target.open("wb") as dst:
                    dst.write(src.read())

        for source_file in sorted((source_dir / "oaat" / year).iterdir()):
            if source_file.suffix.lower() not in {".json", ".csv"}:
                continue
            target = destination / source_file.name
            if target.exists() and not force:
                continue
            target.write_bytes(source_file.read_bytes())

        standalone = next(destination.glob("tarifmatcher-*-standalone.jar"), None)
        if standalone is None:
            raise FileNotFoundError(f"No standalone TarifMatcher JAR found after extracting {zip_path}")
        summary[year] = {
            "zip": str(zip_path),
            "destination": str(destination),
            "standalone_jar": str(standalone),
        }
    return summary


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract official OAAT TarifMatcher ZIPs into local non-git runtime output.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--year", action="append", dest="years", help="Year to extract. Repeat for multiple years. Defaults to all known years.")
    parser.add_argument("--no-force", action="store_true", help="Do not overwrite existing extracted files.")
    args = parser.parse_args(argv)
    summary = prepare_tarifmatcher_runtime(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        years=args.years,
        force=not args.no_force,
    )
    for year, info in summary.items():
        print(f"{year}: {info['standalone_jar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
