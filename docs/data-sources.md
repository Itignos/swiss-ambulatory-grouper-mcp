# Data sources

This repository intentionally does not redistribute official tariff, coding, or generated database files. These external source files are subject to their own licenses, terms of use, and/or access conditions; contributors and users must obtain them directly from the official providers.

## OAAT

Most tariff components required by this project must be obtained from OAAT after registration:

https://oaat-otma.ch/gesamt-tarifsystem/tarifkomponenten-und-software

For the initial importer you need local equivalents of:

- LKAAT source database/export with `LK_*` tables
- TARDOC source database/export with `TD_*` tables
- ambulatory flat-rate catalogue for `AmbP`
- Capitulum/chapter data

The public scripts may help import/convert these files, but neither the original files nor converted copies should be committed.

## BFS ICD-10 / CIM-10

ICD-10/CIM-10 language source files are obtained from BFS medical coding instrument pages:

- German: ICD-10-GM ClaML
- French: CIM-10-GM ClaML
- Italian: ICD-10-GM ClaML

The first importer expects ClaML XML files placed at the paths printed by:

```bash
python scripts/print_source_requirements.py
```

## ICD/CIM source year fallback

The tariff year and the ICD/CIM source year are configured separately. For example, if no BFS 2027 ClaML files are available yet, a 2027 tariff database can be built with locally provided BFS 2026 ICD/CIM files:

```bash
python scripts/build_database.py --year 2027 --icd-year 2026 --force
```

The generated SQLite database stores both values in `import_metadata`:

- `year`: tariff/catalogue year
- `icd_year`: BFS ICD/CIM source year

## Local verification without publishing data

Use:

```bash
python scripts/check_sources.py
```

It reports presence, size, and SHA-256 hashes. Hashes and file sizes are useful for collaboration without sharing the source files themselves.
