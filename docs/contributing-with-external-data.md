# Contributing with external data

Contributions are welcome, but official OAAT/BFS source files and generated SQLite databases must not be included in GitHub.

## Allowed in pull requests

- importer code
- documentation
- synthetic tests and mini-fixtures
- schema or view definitions without copied official rows
- source inventory output with file names, sizes, and hashes

## Not allowed in pull requests or issues

- OAAT downloads or extracted files
- BFS ICD-10/CIM-10 original files
- generated SQLite databases
- large table exports or screenshots containing official catalogue rows
- logs that include private paths or data extracts

## Debugging data-dependent issues

When reporting an issue, run:

```bash
python scripts/check_sources.py
```

Share the status, versions, file sizes, hashes, stack trace, and a minimal synthetic reproducer where possible. Do not upload the official source files.
