# Wildlife Camera Trap System — Design Document

## Project Overview

A personal wildlife monitoring system for a backyard deployment. The system automatically
ingests images from an SD-card-based camera trap, identifies species using AI, stores
detections in a long-term dataset, and provides a local interface for browsing and
correcting results.

## Goals

- Detect and log wildlife events automatically
- Identify species without manual intervention (AI-first, human correction loop)
- Build a clean, queryable long-term dataset
- Remain simple, general, and understandable — the owner is an active engineering partner

## Non-Goals (for now)

- Real-time alerting
- Cloud hosting or remote access

## System Architecture

The system has a clean physical boundary:

- **Field side**: camera trap writes JPEGs to SD card
- **Processing side**: laptop runs the full pipeline when triggered

### Five-phase pipeline

```
[Camera trap] --(SD card)--> [Ingestion] --> [Processing] --> [Storage] --> [Interface]
                                                    ^                            |
                                                    |______ correction loop _____|
                                                    |
                                             [Re-identification]
                                       (MegaDescriptor embeddings +
                                        gallery nearest-neighbor matching)
```

### Phase 1 — Ingestion
- Triggered manually when SD card is offloaded (approximately monthly)
- Associates images with a deployment (camera + location); user selects from a list or creates one interactively; camera make/model pre-filled from EXIF
- Copies new files into organized raw store: `media/YYYY/MM/DD/`
- Extracts EXIF metadata (timestamp, camera settings) at ingest time
- Generates full-image thumbnails, written to `derived/YYYY/MM/DD/`, mirroring the image archive
- Idempotent: running ingestion twice on the same card does not duplicate images
- Enqueues all new images for Phase 2 processing as a batch

### Phase 2 — Processing
- Batch job works through the queue of newly ingested images
- AI classifier produces: species label, confidence score, bounding box
- Classifier is a swappable component (see Decisions log)
- Generates detection crops immediately after classification:
  - Padded crop centred on each detected animal's bounding box
- Metadata writer commits all results to database in a single transaction

### Phase 3 — Storage
- SQLite database holds all detection events and metadata
- Raw images live in `media/` — immutable, never modified or deleted
- Derived assets (thumbnails, crops) live in `derived/` — regenerable at any time
- Database records paths to derived assets, not the assets themselves
- Export available at any time: CSV, JSON

### Phase 4 — Interface
- Local web dashboard served by FastAPI + Uvicorn (Python) with a React (Vite) frontend
- Three-tab layout: Home (summary statistics), Browse (filterable detection grid),
  Analytics (charts and visualizations)
- Phase 4a (first pass) is read-only; label correction is deferred to Phase 4b
- In development: Vite dev server and Uvicorn run as separate processes via `Procfile.dev`
- In production: React app is compiled once by `crittercam build-ui`; `crittercam serve`
  starts a single Uvicorn process that serves both the API and the built static files

### Phase 5 — Individual re-identification
- For each detection crop, compute a MegaDescriptor-L-384 embedding and store it as a
  `.npy` file in `derived/`, referenced by `detections.embedding_path`
- Gallery-based nearest-neighbor matching (cosine similarity) assigns detections to
  individuals; threshold default 0.5 (calibrated on domestic cat; see Decision 025)
- Human confirmations and merges become permanent gallery anchors that survive model
  upgrades (see Decisions 023, 026)
- Results stored in `individuals` table; `detections` gains FK + assignment metadata
- `crittercam identify` — compute embeddings and run gallery matching; `--skip-embedding`
  re-runs matching only (for threshold experimentation without re-embedding)
- `crittercam merge-individuals` — merge two or more individuals into one (Decision 026)
- `crittercam name-individual` — assign a display nickname to an individual

## Technology Choices

| Component | Choice | Status |
|---|---|---|
| Language | Python 3.12 | Decided |
| Build system | setuptools | Decided |
| Database | SQLite | Decided |
| AI classifier | SpeciesNet (swappable) | Decided |
| CLI framework | argparse (stdlib) | Decided |
| Config format | TOML (`tomli-w` for writing) | Decided |
| API framework | FastAPI + Uvicorn | Decided |
| Frontend framework | React + Vite | Decided |
| Chart library | Recharts | Decided |
| Re-ID model | MegaDescriptor-L-384 (`timm`) | Decided |

## Storage Layout

The codebase and the data live in separate locations:

- **Code** — git repository on the laptop (e.g. `~/crittercam/`)
- **Data** — external hard drive (`data_root`), configured at runtime

All paths stored in the database are relative to `data_root`. The pipeline resolves
full paths as `config.data_root / record.path`. This makes the dataset portable and
resilient to the drive remounting at a different absolute path (see DECISIONS.md #010).

```
<data_root>/                         # external hard drive
├── media/YYYY/MM/DD/                # raw image archive — immutable
├── derived/YYYY/MM/DD/              # thumbnails and crops — regenerable
├── db/crittercam.db                 # SQLite database
└── exports/                         # CSV / JSON exports

<repo>/                              # git repository on laptop
├── design/
│   ├── DESIGN.md
│   ├── PHASES.md
│   └── DECISIONS.md
├── CLAUDE.md
├── Procfile.dev                     # runs Uvicorn + Vite simultaneously in dev
├── crittercam/
│   ├── cli/                         # entry point: `crittercam` command
│   │   ├── main.py                  # auto-discovers and registers all cmd_*.py modules
│   │   ├── _geo.py                  # country/admin1 validation + prompts
│   │   ├── cmd_setup.py             # `crittercam setup`
│   │   ├── cmd_ingest.py            # `crittercam ingest`
│   │   ├── cmd_classify.py          # `crittercam classify`
│   │   ├── cmd_identify.py          # `crittercam identify`
│   │   ├── cmd_merge_individuals.py # `crittercam merge-individuals`
│   │   ├── cmd_name_individual.py   # `crittercam name-individual`
│   │   ├── cmd_serve.py             # `crittercam serve`
│   │   ├── cmd_build_ui.py          # `crittercam build-ui`
│   │   └── cmd_clean_db.py          # `crittercam clean-db`
│   ├── config.py                    # config load/save (~/.config/crittercam/config.toml)
│   ├── pipeline/
│   │   ├── db.py                    # connection + migration runner
│   │   ├── exif.py                  # EXIF extraction (Browning camera support)
│   │   ├── ingest.py                # Phase 1 ingestion + thumbnail generation
│   │   ├── classify.py              # Phase 2 classification + crop generation
│   │   ├── identify.py              # Phase 5 re-identification (embed + match)
│   │   ├── clean.py                 # detection/image removal (clean-db command)
│   │   └── migrations/
│   │       ├── 0001_initial_schema.sql
│   │       └── 0002_reid_schema.sql # individuals table + reid columns on detections
│   ├── classifier/
│   │   ├── base.py                  # Detection dataclass + Classifier Protocol
│   │   └── speciesnet.py            # SpeciesNet adapter (google/cameratrapai)
│   ├── identifier/
│   │   ├── base.py                  # Embedding dataclass + Identifier Protocol
│   │   └── megadescriptor.py        # MegaDescriptor-L-384 adapter (timm + HuggingFace)
│   └── web/                         # Phase 4 dashboard
│       ├── api/                     # FastAPI route modules
│       │   ├── __init__.py          # shared get_conn() helper
│       │   ├── detections.py        # GET /api/detections, /api/detections/recent_by_species,
│       │   │                        #     /api/detections/{id}, /api/species, /api/individuals
│       │   └── stats.py             # GET /api/stats/summary, /api/stats/detections_over_time
│       ├── ui/                      # React app (Vite)
│       │   ├── src/
│       │   │   ├── components/
│       │   │   │   ├── StatsBar.jsx           # summary statistics
│       │   │   │   ├── RecentBySpecies.jsx    # most recent crop per species (Home tab)
│       │   │   │   ├── DetectionsOverTime.jsx # weekly line chart (Analytics tab)
│       │   │   │   ├── DetectionGrid.jsx      # paginated grid; browse by species or individual
│       │   │   │   ├── FilterBar.jsx          # mode selector, species/individual dropdown, date range
│       │   │   │   └── DetailPanel.jsx        # crop + full image with SVG bbox overlay
│       │   │   ├── App.jsx
│       │   │   ├── App.css
│       │   │   └── index.css
│       │   ├── index.html
│       │   ├── package.json
│       │   └── vite.config.js       # proxies /api/* and /media/* to localhost:8000 in dev
│       └── server.py                # FastAPI app + StaticFiles mount + uvicorn entry
├── tests/                           # mirrors crittercam/ structure exactly
│   ├── test_config.py
│   ├── cli/
│   │   ├── test_cmd_setup.py
│   │   ├── test_cmd_ingest.py
│   │   ├── test_cmd_classify.py
│   │   ├── test_cmd_identify.py
│   │   ├── test_cmd_merge_individuals.py
│   │   ├── test_cmd_name_individual.py
│   │   ├── test_geo.py
│   │   └── test_cmd_serve.py
│   ├── classifier/
│   │   └── test_speciesnet.py
│   └── pipeline/
│       ├── assets/                  # sample images (e.g. BROWNING.JPG)
│       ├── conftest.py
│       ├── test_classify.py
│       ├── test_db.py
│       ├── test_exif.py
│       ├── test_identify.py
│       └── test_ingest.py
├── pyproject.toml
└── README.md
```

## Configuration

Runtime configuration lives at `~/.config/crittercam/config.toml` (XDG standard).
Created by `crittercam setup`, which also initialises the database. The only required
field is `data_root`:

```toml
data_root = "/media/mattw/wildlifecam"
```

All CLI commands read this file automatically. `--data-root` flag overrides it for
a single run.

## Database Schema

### deployments
One row per camera deployment (camera + location pairing). Camera make/model are stored
here rather than per-image, since all images from a single SD card offload share the
same hardware.

```sql
CREATE TABLE deployments (
    id              INTEGER PRIMARY KEY,
    deployment_name TEXT,             -- optional human-readable name, e.g. 'back_steps'
    location_id     INTEGER,          -- reserved for future FK to a locations table
    location_name   TEXT,             -- e.g. '126_willard_backyard'
    camera_make     TEXT,             -- e.g. 'BROWNING'
    camera_model    TEXT              -- e.g. 'BTC-8EHP5U'
);
```

### media
One row per file. No processing state — that lives in `processing_jobs`.

```sql
CREATE TABLE media (
    id            INTEGER PRIMARY KEY,
    deployment_id INTEGER REFERENCES deployments(id),
    captured_at   TEXT,                      -- EXIF DateTimeOriginal, ISO 8601, nullable
    path          TEXT    NOT NULL UNIQUE,   -- relative to data_root
    filename      TEXT    NOT NULL,
    media_type    TEXT    NOT NULL DEFAULT 'image',  -- 'image' | 'video' | 'audio'
    width         INTEGER,                   -- pixels
    height        INTEGER,                   -- pixels
    ingested_at   TEXT    NOT NULL,
    file_hash     TEXT    NOT NULL UNIQUE,   -- SHA-256, used for deduplication
    file_size     INTEGER NOT NULL,
    temperature_c REAL,                      -- ambient temp from EXIF UserComment
    thumb_path    TEXT                       -- relative to data_root
);
```

### detections
One row per animal per image, per model run.

```sql
CREATE TABLE detections (
    id                       INTEGER PRIMARY KEY,
    media_id                 INTEGER NOT NULL REFERENCES media(id),
    crop_path                TEXT,            -- relative to data_root
    bbox_x                   REAL,            -- normalized (x, y, w, h) in [0, 1]
    bbox_y                   REAL,
    bbox_w                   REAL,
    bbox_h                   REAL,
    label                    TEXT    NOT NULL,
    confidence               REAL    NOT NULL,
    label_assigned_at        TEXT,
    label_assigned_by        TEXT    NOT NULL DEFAULT 'algorithm',
    model_name               TEXT    NOT NULL,
    model_version            TEXT,
    is_active                INTEGER NOT NULL DEFAULT 1,
    created_at               TEXT    NOT NULL,
    -- Phase 5 re-identification columns (added by migration 0002)
    embedding_path           TEXT,            -- relative to data_root; .npy file
    reid_model_name          TEXT,
    reid_model_version       TEXT,
    individual_id            INTEGER REFERENCES individuals(id),
    individual_similarity    REAL,            -- cosine similarity; 1.0 sentinel for founding detections
    individual_assigned_by   TEXT,            -- 'algorithm' | 'human'
    individual_assigned_at   TEXT             -- ISO 8601 timestamp
);
```

### individuals
One row per identified individual animal (added by migration 0002).

```sql
CREATE TABLE individuals (
    id           INTEGER PRIMARY KEY,
    species_leaf TEXT NOT NULL,    -- leaf of taxonomy string, e.g. 'domestic cat'
    nickname     TEXT,             -- null until set via crittercam name-individual
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
```

IDs are gap-filling integers (lowest unused positive integer), so they restart from 1
after a full reset rather than continuing from the historical SQLite maximum.

#### Detection label format

The `label` column stores the full SpeciesNet taxonomy string, not just the species name:

```
<uuid>;<kingdom>;<phylum>;<class>;<order>;<family>;<genus>;<species leaf>
```

Example: `abc123;animalia;chordata;mammalia;carnivora;canidae;canis;canis latrans`

Special categories follow the same pattern with empty intermediate segments:
`abc123;;;;;blank`

The leaf name (final segment after the last `;`) is the only part shown to users.
SQL queries that filter by label must use `LIKE '%;{leaf}'` — never plain equality or `IN`.

### processing_jobs
One row per (subject, algorithm). Tracks pipeline state; results live in their own
tables. Rows can be pruned freely without affecting results.

```sql
CREATE TABLE processing_jobs (
    id           INTEGER PRIMARY KEY,
    media_id     INTEGER REFERENCES media(id),
    detection_id INTEGER REFERENCES detections(id),
    job_type     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    started_at   TEXT,
    completed_at TEXT,
    error_msg    TEXT,
    CHECK (
        (media_id IS NOT NULL AND detection_id IS NULL) OR
        (media_id IS NULL AND detection_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX idx_jobs_image
    ON processing_jobs(media_id, job_type)
    WHERE media_id IS NOT NULL;

CREATE UNIQUE INDEX idx_jobs_detection
    ON processing_jobs(detection_id, job_type)
    WHERE detection_id IS NOT NULL;
```

## Key Design Principles

1. **Simplicity over cleverness** — prefer readable, debuggable code over optimized abstractions
2. **Idempotency** — every pipeline stage should be safe to re-run
3. **Swappability** — the classifier is a plugin, not a core dependency
4. **Data integrity** — never modify or delete raw images; all corrections go in the DB
5. **Transparency** — confidence scores and model provenance are always stored
6. **DB as index, not payload** — the database records what exists and where; heavy data
   (images, derived assets, future embeddings) lives on disk or in specialist stores,
   referenced by path or ID
