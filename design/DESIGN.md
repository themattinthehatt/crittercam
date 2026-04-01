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
- Multi-camera support
- Cloud hosting or remote access

## System Architecture

The system has a clean physical boundary:

- **Field side**: camera trap writes JPEGs to SD card
- **Processing side**: laptop runs the full pipeline when triggered

### Four-phase pipeline

```
[Camera trap] --(SD card)--> [Ingestion] --> [Processing] --> [Storage] --> [Interface]
                                                    ^                            |
                                                    |______ correction loop _____|
```

### Phase 1 — Ingestion
- Triggered manually when SD card is offloaded (approximately monthly)
- Copies new files into organized raw store: `images/YYYY/MM/DD/`
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
- Raw images live in `images/` — immutable, never modified or deleted
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

## Storage Layout

The codebase and the data live in separate locations:

- **Code** — git repository on the laptop (e.g. `~/crittercam/`)
- **Data** — external hard drive (`data_root`), configured at runtime

All paths stored in the database are relative to `data_root`. The pipeline resolves
full paths as `config.data_root / record.path`. This makes the dataset portable and
resilient to the drive remounting at a different absolute path (see DECISIONS.md #010).

```
<data_root>/                         # external hard drive
├── images/YYYY/MM/DD/               # raw image archive — immutable
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
│   │   ├── main.py                  # argument parser + dispatch
│   │   ├── _geo.py                  # country/admin1 validation + prompts
│   │   ├── cmd_setup.py             # `crittercam setup`
│   │   ├── cmd_ingest.py            # `crittercam ingest`
│   │   ├── cmd_classify.py          # `crittercam classify`
│   │   └── cmd_serve.py             # `crittercam serve` and `crittercam build-ui`
│   ├── config.py                    # config load/save (~/.config/crittercam/config.toml)
│   ├── pipeline/
│   │   ├── db.py                    # connection + migration runner
│   │   ├── exif.py                  # EXIF extraction (Browning camera support)
│   │   ├── ingest.py                # Phase 1 ingestion + thumbnail generation
│   │   ├── classify.py              # Phase 2 classification + crop generation
│   │   └── migrations/
│   │       └── 0001_initial_schema.sql
│   ├── classifier/
│   │   ├── base.py                  # Detection dataclass + Classifier Protocol
│   │   └── speciesnet.py            # SpeciesNet adapter (google/cameratrapai)
│   └── web/                         # Phase 4 dashboard
│       ├── api/                     # FastAPI route modules
│       │   ├── detections.py        # GET /api/detections — filterable list
│       │   ├── images.py            # GET /api/images/:id — full image metadata
│       │   └── stats.py             # GET /api/stats/* — analytics endpoints
│       ├── ui/                      # React app (Vite)
│       │   ├── src/
│       │   │   └── components/
│       │   ├── index.html
│       │   ├── package.json
│       │   └── vite.config.js       # proxies /api/* to localhost:8000 in dev
│       └── server.py                # FastAPI app + StaticFiles mount + uvicorn entry
├── tests/                           # mirrors crittercam/ structure exactly
│   ├── test_config.py
│   ├── cli/
│   │   ├── test_cmd_setup.py
│   │   ├── test_cmd_ingest.py
│   │   ├── test_cmd_classify.py
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

### images
One row per file. No processing state — that lives in `processing_jobs`.

```sql
CREATE TABLE images (
    id            INTEGER PRIMARY KEY,
    path          TEXT    NOT NULL UNIQUE,   -- relative to data_root
    filename      TEXT    NOT NULL,
    captured_at   TEXT,                      -- EXIF DateTimeOriginal, ISO 8601, nullable
    ingested_at   TEXT    NOT NULL,
    file_hash     TEXT    NOT NULL UNIQUE,   -- SHA-256, used for deduplication
    file_size     INTEGER NOT NULL,
    width         INTEGER,                   -- pixels
    height        INTEGER,                   -- pixels
    camera_make   TEXT,                      -- EXIF Make, e.g. 'BROWNING'
    camera_model  TEXT,                      -- EXIF Model, e.g. 'BTC-8EHP5U'
    temperature_c REAL,                      -- ambient temp from EXIF UserComment
    thumb_path    TEXT                       -- relative to data_root
);
```

### detections
One row per animal per image, per model run.

```sql
CREATE TABLE detections (
    id            INTEGER PRIMARY KEY,
    image_id      INTEGER NOT NULL REFERENCES images(id),
    label         TEXT NOT NULL,
    confidence    REAL NOT NULL,
    bbox_x        REAL,                 -- normalized (x, y, w, h) in [0, 1]
    bbox_y        REAL,
    bbox_w        REAL,
    bbox_h        REAL,
    crop_path     TEXT,                 -- relative to data_root
    model_name    TEXT NOT NULL,
    model_version TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    human_label   TEXT,
    corrected_at  TEXT
);
```

### processing_jobs
One row per (subject, algorithm). Tracks pipeline state; results live in their own
tables. Rows can be pruned freely without affecting results.

```sql
CREATE TABLE processing_jobs (
    id           INTEGER PRIMARY KEY,
    image_id     INTEGER REFERENCES images(id),
    detection_id INTEGER REFERENCES detections(id),
    job_type     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    started_at   TEXT,
    completed_at TEXT,
    error_msg    TEXT,
    CHECK (
        (image_id IS NOT NULL AND detection_id IS NULL) OR
        (image_id IS NULL AND detection_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX idx_jobs_image
    ON processing_jobs(image_id, job_type)
    WHERE image_id IS NOT NULL;

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
