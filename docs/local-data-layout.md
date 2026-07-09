# Local data layout

Keep all official source files and generated outputs outside this Git repository.

Recommended sibling layout:

```text
_external_data/swiss-ambulatory-grouper-mcp/
  sources/
    oaat/
      2027/
        lkaat/lkaat.sqlite
        tardoc/tardoc.sqlite
        ambp/ambp.csv
    bfs/
      2027/
        icd10/de/icd10_de_claml.xml
        icd10/fr/icd10_fr_claml.xml
        icd10/it/icd10_it_claml.xml
  work/
  output/
```

Configure with:

```bash
export SWISS_AMBULATORY_GROUPER_DATA_DIR=/absolute/path/to/_external_data/swiss-ambulatory-grouper-mcp
```

If the environment variable is not set, the code defaults to a sibling `_external_data/swiss-ambulatory-grouper-mcp` directory next to the repository.

Never place official data under `tests/fixtures`; tests must use synthetic files only.
