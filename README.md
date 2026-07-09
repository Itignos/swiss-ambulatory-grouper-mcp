# Swiss Ambulatory Grouper MCP

Open-source tooling to build a **local SQLite database** for the Swiss ambulatory tariff system from officially obtained source files. A Model Context Protocol (MCP) server will be added later on top of this database; this first project phase focuses on reproducible local data preparation.

> [!IMPORTANT]
> This repository contains **no OAAT tariff data**, **no BFS ICD-10/CIM-10 source files**, and **no generated SQLite database**. The scripts are public; the official source files and generated outputs must stay outside GitHub.

## What you need before you can begin

You must obtain the required source files yourself and place them in a local non-git data directory.

### OAAT tariff components and software

Most tariff source files are obtained from OAAT after registration:

https://oaat-otma.ch/gesamt-tarifsystem/tarifkomponenten-und-software

For the first importer version, prepare local files for:

- LKAAT source database/export containing `LK_*` tables
- TARDOC source database/export containing `TD_*` tables
- Ambulatory flat-rate catalogue (`AmbP`) as CSV
- Capitulum/chapter table as CSV

If OAAT provides a different technical format, convert it locally to the expected SQLite/CSV files. Do not commit either the originals or the converted files.

### BFS ICD-10 / CIM-10 source files

ICD-10/CIM-10 language versions come from the Swiss Federal Statistical Office (BFS) medical coding instrument pages:

- DE: ICD-10-GM ClaML via the German BFS medical coding instruments page
- FR: CIM-10-GM ClaML via the French BFS instruments de codage médical page
- IT: ICD-10-GM ClaML via the Italian BFS strumenti di codifica medica page

The importer expects one local ClaML XML file per language.

## Local data layout

Recommended layout outside this Git repository:

```text
_external_data/swiss-ambulatory-grouper-mcp/
  sources/
    oaat/
      2027/
        lkaat/lkaat.sqlite
        tardoc/tardoc.sqlite
        ambp/ambp.csv
        capitulum/capitulum.csv
    bfs/
      2027/
        icd10/de/icd10_de_claml.xml
        icd10/fr/icd10_fr_claml.xml
        icd10/it/icd10_it_claml.xml
  work/
  output/
    swiss_ambulatory_2027.sqlite
```

Set the workspace explicitly:

```bash
export SWISS_AMBULATORY_GROUPER_DATA_DIR=/absolute/path/to/local/non-git-data/swiss-ambulatory-grouper-mcp
```

or copy `.env.example` to `.env` for your local shell tooling. `.env` is ignored by git.

## Quickstart

```bash
git clone https://github.com/<org>/swiss-ambulatory-grouper-mcp.git
cd swiss-ambulatory-grouper-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

cp .env.example .env
# edit .env or export SWISS_AMBULATORY_GROUPER_DATA_DIR manually

python scripts/print_source_requirements.py
python scripts/check_sources.py
python scripts/build_database.py --force
```

`check_sources.py` prints missing local files and official source URLs. `build_database.py` only runs after all required local sources are present.

## Current import scope

The first phase imports only:

- `LK_*` tables from the local LKAAT SQLite source
- `TD_*` tables from the local TARDOC SQLite source
- `AmbP` from CSV
- `Capitulum` from CSV
- multilingual ICD-10/CIM-10 DE/FR/IT from BFS ClaML XML into `ICD10_Code` and `ICD10_Rubric`

Not included yet:

- MCP server tools
- AmbP simulation/grouper execution
- Itignos-specific lookup/transcoding/fuzzy matching
- proprietary/manual correction datasets

## Development

```bash
pip install -e '.[dev]'
pytest -q
```

Tests use synthetic mini-fixtures only. Do not add official OAAT/BFS data to tests, issues, pull requests, or examples.

## License

Code is licensed under Apache-2.0. This license applies to the repository code only, not to any external OAAT/BFS source data that users obtain separately.
