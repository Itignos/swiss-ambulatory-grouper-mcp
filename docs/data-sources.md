# Data sources

This repository intentionally does not redistribute official tariff, coding, or generated database files.

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

## Local verification without publishing data

Use:

```bash
python scripts/check_sources.py
```

It reports presence, size, and SHA-256 hashes. Hashes and file sizes are useful for collaboration without sharing the source files themselves.
