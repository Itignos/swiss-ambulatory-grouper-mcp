# Local Docker runtime

This project can run a first local Docker skeleton that contains both runtime processes in one container:

- Python MCP/runtime HTTP process
- Java TarifMatcher bridge process on localhost inside the container

The official OAAT TarifMatcher ZIP/JAR files and generated SQLite databases are **not** part of this repository and must be mounted from a private local directory.

## Prepare private runtime files

Expected local OAAT ZIP files:

```text
sources/oaat/2026/tarifmatcher-1.1.0.zip
sources/oaat/2027/tarifmatcher-1.2.0.zip
```

Extract them into the non-git output runtime directory:

```bash
python scripts/prepare_tarifmatcher_runtime.py \
  --source-dir /Users/mgeissbu/Itignos/1-Projets/20260709_opensource_swiss-ambulatory-grouper-mcp/sources \
  --output-dir /Users/mgeissbu/Itignos/1-Projets/20260709_opensource_swiss-ambulatory-grouper-mcp/output
```

This creates for example:

```text
output/runtime/tarifmatcher/2027/tarifmatcher-1.2.0-standalone.jar
```

The ZIPs and extracted JARs stay outside GitHub.

## Build local SQLite first

The Docker runtime expects the SQLite database in the same private output directory:

```text
output/swiss_ambulatory_2027.sqlite
```

Build it with the existing importer before starting Docker.

## Start local Docker runtime

```bash
docker compose -f docker-compose.example.yml up --build
```

Smoke test:

```bash
curl http://localhost:3000/health
```

Grouper example:

```bash
curl -s http://localhost:3000/grouper/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "sex":"M",
    "age_years":60,
    "age_days":0,
    "entry_date":"2027-01-15",
    "diagnosis":"L70.1",
    "services":[
      {"code":"C09.KE.0310","quantity":1},
      {"code":"WA.10.0040","quantity":1}
    ]
  }'
```

Mapper validation example:

```bash
curl -s http://localhost:3000/mapper/map \
  -H 'Content-Type: application/json' \
  -d '{
    "sex":"M",
    "age_years":60,
    "age_days":0,
    "entry_date":"2027-01-15",
    "diagnosis":"R59.0",
    "services":[
      {"code":"AA.00.0010","quantity":1},
      {"code":"AA.00.0080","quantity":1}
    ]
  }'
```

The mapper example returns `ok:false` and a `TARDOC_VALIDATION_DELETE` log entry because `AA.00.0080` is not combinable with `AA.00.0010`.

Grouper example with an ATC drug:

```bash
curl -s http://localhost:3000/grouper/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "sex":"M",
    "age_years":30,
    "age_days":0,
    "entry_date":"2027-01-15",
    "diagnosis":"F22.8",
    "services":[
      {"code":"C00.XD.0010","quantity":1}
    ],
    "drugs":[
      {"code":"V09AB03","dose":200,"unit":"mcg"}
    ]
  }'
```

This currently returns group `C00.82B` with `118646` tax points for the mounted 2027 runtime.

LKAAT service search example:

```bash
curl -s http://localhost:3000/lookup/lkaat/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Konsultation","language":"de","limit":5}'
```

LKAAT service details example:

```bash
curl -s http://localhost:3000/lookup/lkaat/details \
  -H 'Content-Type: application/json' \
  -d '{"code":"CA.00.0010","language":"de"}'
```

Diagnosis search example:

```bash
curl -s http://localhost:3000/lookup/diagnoses/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Varizen","language":"de","limit":10}'
```

Supported lookup languages are `de`, `fr`, and `it`. LKAAT lookup reads from `LK_LEISTUNG`, `LK_LEISTUNG_TEXT`, and related lookup tables in the generated SQLite database. Diagnosis lookup reads from `ICD10_Code` and `ICD10_Rubric`.

Expected for the current runtime:

- Python runtime responds.
- Java bridge responds.
- Runtime file status shows the mounted 2027 TarifMatcher standalone JAR, OAAT JSON/CSV files, and SQLite DB.
- Grouper requests are evaluated by the official OAAT Java API.
- Mapper requests are evaluated by the official OAAT Java API and include added TARDOC tarpos plus mapper log entries.
- Lookup requests search LKAAT services/details and ICD-10 diagnoses in the mounted generated SQLite database.
- Casemaster endpoint currently returns a structured “adapter not wired yet” response until its adapter is implemented.

## Export local Docker image outside GitHub

The image itself must not be committed. If a local image archive is needed, save it into the private output directory:

```bash
mkdir -p /absolute/path/to/output/docker
docker save swiss-ambulatory-grouper-mcp-swiss-ambulatory-grouper-mcp:latest \
  | gzip > /absolute/path/to/output/docker/swiss-ambulatory-grouper-mcp-local-latest.tar.gz
```

For this local setup the image archive belongs under:

```text
/Users/mgeissbu/Itignos/1-Projets/20260709_opensource_swiss-ambulatory-grouper-mcp/output/docker/
```

## Current endpoint status

```text
GET  /health              wired
POST /grouper/evaluate    wired to OAAT PatientClassificationSystem.evaluate()
POST /mapper/map                 wired to OAAT Mapper.mapByValue()
POST /lookup/lkaat/search        wired to SQLite LK_LEISTUNG/LK_LEISTUNG_TEXT
POST /lookup/lkaat/details       wired to SQLite LK_LEISTUNG details
POST /lookup/diagnoses/search    wired to SQLite ICD10_Code/ICD10_Rubric
```

The Java bridge also exposes internal endpoints:

```text
GET  /health              wired
POST /grouper/evaluate    wired
POST /mapper/map          wired
POST /casemaster/apply    placeholder
```

## Infomaniak target

The final hosting target is Infomaniak Managed Kubernetes, not Railway. Phase 1 should deploy the same combined image as one Kubernetes Deployment with a private read-only runtime volume.

Later, if needed, the Python MCP process and Java TarifMatcher bridge can be split into separate Kubernetes Deployments without changing the MCP tool contract.
