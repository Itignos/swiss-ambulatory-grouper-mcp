# Swiss Ambulatory Grouper MCP

Open-source tooling to build a **local SQLite database** for the Swiss ambulatory tariff system from officially obtained source files, plus a local Docker runtime for OAAT TarifMatcher grouping/mapping and SQLite-backed catalogue lookup services.

> [!IMPORTANT]
> This repository contains **no OAAT tariff data**, **no BFS ICD-10/CIM-10 source files**, and **no generated SQLite database**. The scripts are public; the official source files and generated outputs must stay outside GitHub. These source files are subject to their own licenses, terms of use, and/or access conditions, so they cannot be redistributed from this repository.

## What you need before you can begin

You must obtain the required source files yourself and place them in a local non-git data directory.

### OAAT tariff components and software

Most tariff source files are obtained from OAAT after registration:

https://oaat-otma.ch/gesamt-tarifsystem/tarifkomponenten-und-software

For the first importer version, the currently expected OAAT files are:

```text
sources/oaat/2026/
  LKAAT_v1.0c_260402_Leistungskatalog_ambulante_Arzttarife.db
  Anhang_A2_Katalog_des_TARDOC_1.4c_251128_2.db
  250808_Anhang_A1_Katalog_der_Ambulanten_Pauschalen_CSV_v1.1c.csv

sources/oaat/2027/
  Leistungskatalog_ambulante_Arzttarife__LKAAT__1.1.db
  Anhang_A2_TARDOC_1.5.db
  Anhang_A1_Katalog_der_Ambulanten_Pauschalen_1.2.csv
```

Notes:

- The official OAAT technical delivery is typically a Microsoft Access database (`.mdb` / `.accdb`). Before running this importer, convert the relevant Access databases locally to SQLite (`.db` / `.sqlite`).
  - macOS example: [MDB ACCDB Viewer](https://apps.apple.com/ch/app/mdb-accdb-viewer/id417392270?l=de-DE&mt=12) can export Access databases for local conversion workflows.
  - On Windows, Microsoft Access itself may be sufficient for exporting the tables into an intermediate format that can then be imported into SQLite.
- LKAAT source tables are exported as `LK_*` tables in the generated SQLite database.
- TARDOC source tables are exported as `TD_*` tables in the generated SQLite database.
- The `Capitulum` table is generated from the chapter rows in the AmbP catalogue.
- Temporary Access/SQLite tables such as `~TMPCLP102981` are ignored.
- Do not commit either the OAAT originals or locally converted files.

### BFS ICD-10 / CIM-10 source files

ICD-10/CIM-10 language versions come from the Swiss Federal Statistical Office (BFS) medical coding instrument pages:

- DE: [BFS Medizinische Kodierung / ICD-10-GM](https://www.bfs.admin.ch/bfs/de/home/statistiken/gesundheit/nomenklaturen/medkk/instrumente-medizinische-kodierung.html)
- FR: [BFS instruments de codage médical / CIM-10-GM](https://www.bfs.admin.ch/bfs/fr/home/statistiques/sante/nomenclatures/medkk/instruments-codage-medical.html)
- IT: [BFS strumenti di codifica medica / ICD-10-GM](https://www.bfs.admin.ch/bfs/it/home/statistiche/salute/nomenclature/medkk/strumenti-codifica-medica.html)

Currently expected BFS 2026 files:

```text
sources/bfs/2026/
  icd10gm2026syst-claml/Klassifikationsdateien/icd10gm2026syst_claml_20250912.xml
  dz-f-14.04.01-cim10-gm-2024-02-ClaML-SI/CIM10GM2024_ClaML_S_FR_20241031.xml
  dz-i-14.04.01-cim10-gm-2024-02-ClaML-SI/ICD10GM2024_ClaML_S_IT_20241031.xml
```

If a tariff year uses a different ICD/CIM source year, pass `--icd-year`, for example building the 2027 tariff with currently available 2026 ICD/CIM files:

```bash
python scripts/build_database.py --year 2027 --icd-year 2026 --force
```

> [!NOTE]
> At the moment, the 2027 build can be created with BFS ICD-10/CIM-10 source files from 2026 (`--icd-year 2026`) if no separate BFS 2027 ClaML files are available yet. This does **not** mean that ICD/CIM content was published by this repository; it only records that the local 2027 SQLite build uses the locally provided BFS 2026 ICD/CIM files. The selected ICD/CIM source year is stored in the generated database table `import_metadata` as `icd_year`.

## Local data layout

Recommended layout outside this Git repository:

```text
_external_data/swiss-ambulatory-grouper-mcp/
  sources/
    oaat/
      2026/
      2027/
    bfs/
      2026/
      2027/              # when available
  work/
  output/
    swiss_ambulatory_2026.sqlite
    swiss_ambulatory_2027.sqlite
```

Set the workspace explicitly:

```bash
export SWISS_AMBULATORY_GROUPER_SOURCE_DIR=/absolute/path/to/sources
export SWISS_AMBULATORY_GROUPER_OUTPUT_DIR=/absolute/path/to/output
```

or copy `.env.example` to `.env` for your local shell tooling. `.env` is ignored by git.

## Quickstart

```bash
git clone https://github.com/<org>/swiss-ambulatory-grouper-mcp.git
cd swiss-ambulatory-grouper-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

python scripts/print_source_requirements.py --year 2026
python scripts/check_sources.py --year 2026
python scripts/build_database.py --year 2026 --force

python scripts/print_source_requirements.py --year 2027 --icd-year 2026
python scripts/check_sources.py --year 2027 --icd-year 2026
python scripts/build_database.py --year 2027 --icd-year 2026 --force
```

`check_sources.py` prints missing local files and official source URLs. `build_database.py` only runs after all required local sources are present.

## Current import scope

The first phase imports only:

- LKAAT source tables into `LK_*` output tables
- TARDOC source tables into `TD_*` output tables
- `AmbP` from CSV
- `Capitulum` generated from AmbP chapter rows
- multilingual ICD-10/CIM-10 DE/FR/IT from BFS ClaML XML into `ICD10_Code` and `ICD10_Rubric`

Not included yet:

- Casemaster adapter execution
- production MCP transport wiring beyond the current local HTTP runtime
- Itignos-specific lookup/transcoding/fuzzy matching
- proprietary/manual correction datasets

## Local Docker runtime

A local Docker runtime is available for grouping, mapping, and catalogue lookup. It runs one combined container with:

- Python MCP/runtime HTTP process
- Java TarifMatcher bridge process
- private runtime files mounted from the local non-git `output/` directory
- generated SQLite database mounted read-only for LKAAT/ICD-10 lookup

Prepare the official OAAT TarifMatcher ZIPs from your private `sources/` directory into `output/runtime/`:

```bash
python scripts/prepare_tarifmatcher_runtime.py \
  --source-dir /absolute/path/to/sources \
  --output-dir /absolute/path/to/output
```

Then start locally:

```bash
docker compose -f docker-compose.example.yml up --build
curl http://localhost:3000/health
```

The current Java bridge loads the official OAAT TarifMatcher JAR at runtime and wires the Grouper and Mapper APIs. The Python runtime also exposes SQLite-backed lookup endpoints for LKAAT service search/details and ICD-10 diagnosis search. Casemaster remains a structured placeholder until its adapter is implemented. See [`docs/local-docker-runtime.md`](docs/local-docker-runtime.md).

## Development

```bash
pip install -e '.[dev]'
pytest -q
```

Tests, if present locally, must use synthetic mini-fixtures only. Do not add official OAAT/BFS data to tests, issues, pull requests, or examples.

## License

Code is licensed under Apache-2.0. This license applies to the repository code only, not to any external OAAT/BFS source data that users obtain separately.
