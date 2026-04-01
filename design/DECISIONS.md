# Architectural Decisions Log

A running record of meaningful choices made during this project — what we chose,
what we considered, and why. Useful for revisiting assumptions and onboarding
future-you to past-you's reasoning.

---

## 001 — SQLite as the database

**Date**: project start
**Decision**: Use SQLite for all detection event storage

**Considered**:
- PostgreSQL — more powerful, but requires a running server process; overkill for
  a single-user local system
- Flat files (CSV/JSON) — simple to write, but poor for querying and grows unwieldy
- SQLite — serverless, single file, excellent Python support, queryable with standard
  SQL, trivially portable and backed up

**Rationale**: This is a single-user local system. SQLite is the right tool at this
scale. The database file can be copied, backed up, or opened with any SQLite browser.
If the dataset ever grows large enough to need Postgres, migration is straightforward.

---

## 002 — AI classifier as a swappable component

**Date**: project start
**Decision**: The classifier will be isolated behind a clean interface, not coupled
to the pipeline

**Considered**:
- Hard-coding a specific model (e.g. MegaDetector) into the processing pipeline
- Building a plugin/adapter layer from the start

**Rationale**: We don't yet know which classifier is best for this backyard deployment.
Wildlife AI is a fast-moving space. Isolating the classifier means we can swap models,
try an API-based approach, or run multiple classifiers in parallel without rewriting
the pipeline. The interface contract is simple: takes an image path, returns a list
of detections with labels and confidence scores.

---

## 003 — Raw images are immutable

**Date**: project start
**Decision**: Raw images copied from SD card are never modified or deleted by the system

**Rationale**: The raw image is ground truth. All corrections, annotations, and
derived data live in the database. This means we can always re-process from scratch,
and a database corruption or bad classifier run never destroys original data.

---

## 004 — Local-first, no cloud dependency

**Date**: project start
**Decision**: The system runs entirely on the always-on laptop; no cloud services required

**Considered**:
- Cloud VM for processing (more compute, more complexity, ongoing cost)
- Hybrid: local ingestion, cloud processing

**Rationale**: Backyard deployment means reliable home network access. A local system
is simpler to debug, has no API costs, and keeps wildlife data private. Export to
cloud storage can be added later as an optional backup, not a dependency.

---

## 005 — Batch ingestion, not streaming

**Date**: post-start
**Decision**: The pipeline is designed around periodic batch ingestion (monthly SD
card offloads), not a continuous event-driven stream

**Considered**:
- Always-on file watcher (inotify/watchdog) triggering per-image processing as
  files arrive — assumed in the original design
- Manual or mount-triggered batch job that processes all new images at once

**Rationale**: The camera trap is physically retrieved and the SD card manually
offloaded approximately monthly. There is no live feed. Designing around a streaming
model would add complexity (long-running watcher process, per-image queue overhead)
that doesn't match actual usage. A batch job is simpler, easier to reason about,
and easier to re-run if something goes wrong.

**Implications**:
- Phase 1 ingestion is a batch job, not a continuous watcher
- Phase 2 processing works through a burst queue, not a steady drip
- SQLite bulk load optimisations apply on every ingestion run:
  drop indexes → insert all rows in a single transaction → rebuild indexes
- `PRAGMA synchronous = OFF` and `PRAGMA journal_mode = MEMORY` during the
  bulk insert window are appropriate; restore defaults afterward
- The "always-on" framing in the original design doc should be understood as
  "the laptop is always available," not "the pipeline is always running"

---

## 006 — Derived assets stored on disk, referenced by path in the database

**Date**: post-start
**Decision**: Derived assets (thumbnails, crops, and any future generated files) are
written to disk in a mirrored directory structure and referenced in the database by
path, not stored as blobs in the database itself

**Considered**:
- Storing derived asset data directly in SQLite as BLOBs
- Storing paths in SQLite and files on disk (chosen)

**Rationale**: The database is an index of what exists and where — not the payload
itself. Storing paths keeps the database lean, makes derived assets directly accessible
by other tools (a browser, a file manager, a notebook), and means a corrupt or
accidentally deleted derived asset doesn't take down any database structure with it.
Derived assets can always be regenerated from the original; the database just needs
to know where to find them.

**Directory structure**:
```
images/
  YYYY/MM/DD/
    <filename>.jpg          # original, immutable (Decision 003)
derived/
  YYYY/MM/DD/
    <filename>_thumb.jpg    # full-image thumbnail
    <filename>_det001.jpg   # crop for detection 1
    <filename>_det002.jpg   # crop for detection 2
```

The date-mirrored structure keeps originals and derived assets visually paired
and makes bulk operations (backup, regeneration) straightforward.

---

## 007 — Cropped detection images as a first-class derived asset

**Date**: post-start
**Decision**: For each detection, generate and store a cropped image centred on the
bounding box returned by MegaDetector, with configurable padding

**Rationale**: Camera trap images contain large amounts of static background. The
animal is often a small subject in a large frame. A padded crop makes the dashboard
significantly more useful — thumbnails show the animal rather than an empty scene —
and reduces the data that needs to be loaded for browsing.

**Implications**:
- Crops are generated immediately after MegaDetector runs, as part of Phase 2
  processing; they are not deferred to render time
- Padding (suggested default: 15-20% of bounding box dimensions, clamped to image
  boundary) should be a configurable parameter, not a hardcoded constant
- One crop is generated per detection, not per image — an image with two animals
  produces two crop files
- This reinforces the need for a separate `detections` table (one row per animal
  per image) distinct from the `images` table (one row per file); each detection
  row holds its own bounding box, confidence, species label, and crop path
- Images where MegaDetector finds nothing have no detection rows and no crops;
  they are logged in the `images` table as empty frames

---

## 008 — Embeddings deferred; storage strategy not yet decided

**Date**: post-start
**Decision**: Generating and storing CLIP embeddings (or similar) is a desirable
future capability but the storage strategy is not decided yet

**Considered**:
- SQLite BLOB column — works fine for storage and retrieval by ID; a CLIP embedding
  is ~2-3 KB, so scale is not the concern
- Dedicated vector store (e.g. ChromaDB, Qdrant) running as a local library —
  necessary if similarity search is needed; links to SQLite via detection ID
- Flat files (numpy .npy, Parquet) — simplest for offline analysis in notebooks;
  no query capability
- PostgreSQL + pgvector — the Immich path; powerful but reintroduces a server
  process (conflicts with Decision 001)

**Rationale**: The right storage choice depends on the intended use. If embeddings
are only needed for offline batch analysis (clustering, dimensionality reduction),
a flat file or SQLite BLOB is sufficient. If the dashboard needs live similarity
search ("show me images like this one"), a vector store becomes necessary. That
use case is not yet defined, so the decision is deferred.

**Key principle established**: The question is not whether SQLite can hold embeddings
(it can), but whether SQL is the right query model for the intended operation.
Similarity search requires a vector index, which is outside standard SQLite's
capabilities.

---

## 009 — SHA-256 file hash as deduplication key

**Date**: 2026-03-27
**Decision**: Use SHA-256 hash of the file contents as the deduplication key for ingestion

**Considered**:
- Composite of (filename, file_size, captured_at) — fast, no I/O, but theoretically fallible
- SHA-256 of file contents — requires reading every file, but guarantees correctness

**Rationale**: Trail cam offloads are infrequent and files are large-ish JPEGs, so the
I/O cost of hashing at ingest time is acceptable. A composite key could miss a duplicate
if any field differs (e.g., filename collision from a different card). Hash is unambiguous.

**Implications**:
- `images.file_hash` is `UNIQUE NOT NULL`
- Ingestion checks hash before copying; if hash exists, skip
- Hash is computed once at ingest and never recomputed

---

## 010 — Paths stored relative to a configurable data root

**Date**: 2026-03-27
**Decision**: All file paths stored in the database are relative to a `data_root`
config value, not absolute

**Considered**:
- Absolute paths — simple to write, fragile if the drive remounts at a different path
- Relative paths resolved against a config value — one config change handles remounts

**Rationale**: The database and image archive will live together on an external hard
drive. External drives don't always mount at the same absolute path. Storing relative
paths means the system survives remounts and makes the dataset portable to another
machine by updating one config value.

**Implications**:
- `images.path` stores e.g. `images/2026/03/15/IMG_001.jpg`, never an absolute path
- `derived/` paths follow the same convention
- All pipeline code resolves full paths as `config.data_root / record.path`
- `data_root` is a required config value, not a default

---

## 011 — processing_jobs table tracks per-algorithm state; status removed from images

**Date**: 2026-03-27
**Decision**: Processing state for each algorithm lives in a dedicated `processing_jobs`
table keyed by (subject, job_type), not as a `status` field on `images`

**Considered**:
- `status` column on `images` — simple, but implicitly assumes one pipeline per image;
  breaks when a second algorithm (e.g. weather inference) is added
- `processing_jobs` table — more rows, but scales to any number of algorithms and
  subject types without schema changes

**Rationale**: The pipeline will eventually run multiple independent algorithms per
image (detection, weather, re-identification, etc.), and some algorithms run on
detection crops rather than full images. A single `status` field cannot represent
this. A separate table with one row per (subject, job_type) is the correct model.

**Schema**:
```sql
CREATE TABLE processing_jobs (
    id           INTEGER PRIMARY KEY,
    image_id     INTEGER REFERENCES images(id),
    detection_id INTEGER REFERENCES detections(id),
    job_type     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | running | done | error
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

**Implications**:
- `images` table has no processing state columns
- `is_empty` (whether a detection run found no animals) is derived at query time from
  the absence of active detection rows, not stored on `images`
- Adding a new algorithm requires no schema change — only new `job_type` values
- Jobs can target images (`image_id`) or detection crops (`detection_id`); the CHECK
  constraint enforces exactly one subject per row
- Old job rows can be deleted freely; results live in their own tables

---

## 012 — is_active flag on detections tracks the current model run

**Date**: 2026-03-27
**Decision**: `detections` has an `is_active` boolean (integer) column; re-running
a new model inserts new rows (is_active = 1) and marks old rows inactive (is_active = 0)

**Considered**:
- Deleting old detection rows on model swap — destroys history, prevents comparison
- Filtering by latest model_name/version at query time — complex queries everywhere
- `is_active` flag — simple queries, history preserved, easy to flip

**Rationale**: AI models improve over time. We want to swap classifiers without losing
prior results, and we want the dashboard to show a consistent "current" view without
complex query logic. `is_active = 1` is the simple filter that achieves this.

**Implications**:
- Dashboard queries always include `WHERE is_active = 1`
- When a new model run completes, old rows for those images are set `is_active = 0`
  and new rows are inserted with `is_active = 1`
- Historical analysis can ignore the filter and compare across model versions
- Human corrections are stored as fields on the detection row and do not affect
  `is_active`; the AI-generated fields are never modified (Decision 003)

---

## 013 — argparse over third-party CLI frameworks

**Date**: 2026-03-28
**Decision**: Use Python's stdlib `argparse` for the CLI, not Click or Typer

**Considered**:
- Click — popular, decorator-based, good UX; adds a dependency
- Typer — Click wrapper with type annotations; adds two dependencies
- argparse — verbose but zero dependencies; ships with Python

**Rationale**: The CLI has a small number of subcommands and the project philosophy
is to minimise dependencies. argparse is sufficient and means one fewer thing to
install, update, or break.

---

## 014 — Config file at ~/.config/crittercam/config.toml

**Date**: 2026-03-28
**Decision**: Runtime config lives at `~/.config/crittercam/config.toml`, following
the XDG base directory convention

**Considered**:
- `~/.crittercamrc` — common but clutters the home directory
- `<repo>/.env` or `<repo>/config.toml` — couples config to the repo; wrong for
  user-specific paths like `data_root`
- `~/.config/crittercam/config.toml` — XDG standard; clean, predictable, user-scoped

**Rationale**: Config is user-specific (it contains a path to an external drive) and
should not live in the repo. The XDG location is standard on Linux and works on macOS.

**Implications**:
- Created by `crittercam setup`; not checked into git
- CLI flag `--data-root` overrides `data_root` for a single invocation
- `tomllib` (stdlib, read-only) + `tomli-w` (write) handle serialisation

---

## 015 — Hand-rolled versioned migration scripts over Alembic

**Date**: 2026-03-28
**Decision**: Database migrations are plain numbered SQL files applied by a small
custom runner, not managed by Alembic

**Considered**:
- Alembic — industry-standard migration tool; auto-generates migrations from ORM
  models; significant learning curve and configuration overhead
- Hand-rolled versioned SQL files — transparent, no new concepts, ~50 lines of Python

**Rationale**: Schema changes will be infrequent and deliberate. Alembic's power
(auto-generation, ORM integration) is not needed here. A simple version table plus
numbered SQL files is easier to understand and debug, which matters for a learning
project.

**Structure**:
```
crittercam/pipeline/migrations/
    0001_initial_schema.sql
    0002_<description>.sql
    ...
```

The runner checks `schema_migrations` for applied versions, runs pending files in
order, and records each. Safe to re-run — already-applied migrations are skipped.

---

## 016 — SpeciesNet chosen as Phase 2 classifier

**Date**: 2026-03-28
**Decision**: Use SpeciesNet (google/cameratrapai) as the Phase 2 classifier,
running fully locally

**Considered**:
- MegaDetector alone — gives bounding boxes and animal/human/vehicle labels but
  no species ID; good escape hatch if SpeciesNet setup proves painful, but loses
  the main value of Phase 2
- MegaDetector + iNaturalist classifier (DIY ensemble) — iNaturalist models are
  trained on observer-submitted photos, not camera trap images; IR, motion blur,
  and small-subject-in-large-frame distributions differ significantly; would also
  require building our own ensemble logic
- Wildlife Insights API — hosted deployment of the same SpeciesNet model; ruled
  out because it sends images to Google's servers (conflicts with Decision 004)
  and adds a network dependency to the batch pipeline
- General-purpose vision LLMs (GPT-4o, Gemini Vision) — cloud dependency,
  unstructured output, uncalibrated confidence scores, no bounding boxes;
  ruled out for the same reasons as Wildlife Insights API

**Rationale**: SpeciesNet is the strongest fit for a fixed backyard deployment:
- Trained on 65M+ camera trap images (not observer photos), so the image
  distribution matches closely
- Taxonomic rollup — falls back to genus/family rather than guessing wrong at
  species level; correct behavior for a dataset that needs to be trusted over time
- Blank detection — handles wind-triggered empty frames explicitly, which camera
  traps produce in volume
- Returns bounding boxes (via the internal MegaDetector component) feeding
  directly into crop generation (Decision 007) without additional wiring
- Fully local, no API cost, no data leaves the machine (consistent with
  Decision 004)

**Implications**:
- Model weights download from Kaggle on first run; can be pre-downloaded for
  offline operation
- PyTorch is a significant dependency; GPU optional but recommended for batch
  throughput
- The classifier interface (Decision 002) wraps SpeciesNet so it can be swapped
  later without touching the pipeline
- Geofencing (country/state filtering) was a feature of the ensemble step and is
  currently inactive; see Decision 018

---

## 017 — SpeciesNet output mapping: one detection row per image, top bbox

**Date**: 2026-03-29
**Decision**: Each processed image produces at most one detection row in the
`detections` table. The species label and confidence come from the top entry in
`SpeciesNetClassifier`'s `classifications.classes` / `classifications.scores`
arrays (see Decision 018 for why the ensemble is bypassed). The bounding box
columns (`bbox_x`, `bbox_y`, `bbox_w`, `bbox_h`) are populated from the
highest-confidence detection returned by `SpeciesNetDetector`. Images where the
classifier returns `"blank"` or no classes produce a detection row with the
appropriate label and null bbox columns.

**Considered**:
- One row per detector bounding box — the detector may return multiple boxes
  when multiple animals are in frame, but the classifier produces one label per
  image (not per box). Multiple rows sharing the same species label would be
  redundant and misleading.
- One row per image using the top bbox (chosen) — matches the classifier's actual
  output granularity. The top detection box is used for crop generation
  (Decision 007); using the same box for the detection row is consistent.
- Storing raw top-5 classifications as an additional column — deferred.
  The structured label and confidence fields cover all current query needs.
  If top-5 data becomes useful later, a column can be added via migration.

**Rationale**: The classifier produces one label per image, not one label per
animal. Designing the schema around that actual contract avoids fabricating a
per-box species breakdown the model does not provide. The top-bbox choice is
consistent with crop generation (Decision 007), which also operates on the
single highest-confidence detection.

**SpeciesNet fields → detection row mapping**:
- `classifications.classes[0]` → `label` (normalized to lowercase)
- `classifications.scores[0]`  → `confidence`
- `detections[0].bbox`         → `bbox_x/y/w/h` (top detection; null if absent
                                   or label is `"blank"`)
- `model_version`              → `model_version`
- Bbox format: SpeciesNet returns `[xmin, ymin, width, height]` normalized 0–1;
  stored as-is in `bbox_x/y/w/h` — no conversion required

**Blank and empty frame handling**:
- `classes[0] == "blank"` → detection row with `label='blank'`, null bbox, null crop_path
- Classifier failure → log error in processing_jobs, no detection row inserted

---

## 018 — SpeciesNet ensemble disabled; classifier-only mode with bbox-guided preprocessing

**Date**: 2026-03-29
**Decision**: The `SpeciesNetEnsemble` step is bypassed. The pipeline runs
`SpeciesNetDetector` and `SpeciesNetClassifier` directly and reads the top
classification from `classifications.classes[0]` / `scores[0]`.

**Considered**:
- Full ensemble (original design) — combines detector, classifier, and geolocation
  into a single `prediction` field via `SpeciesNetEnsemble.combine()`
- Classifier-only (chosen) — call classifier directly; read top-1 class from its
  output; use detector bbox only to guide the classifier crop

**Rationale**: In initial field runs, the ensemble's `prediction_source` was
almost always `"detector"` for backyard camera trap images. The detector produces
coarse labels (`animal`, `bird`) rather than species-level ones. The ensemble
promotes the detector's answer when the classifier is uncertain — which is the
common case for small subjects in wide frames (squirrels, songbirds). Bypassing
the ensemble and reading directly from the classifier returns the actual top-1
species prediction, including taxonomic rollups when confidence is low.

**How classifier-only mode works**:
1. `SpeciesNetDetector.predict()` runs on the full image to get bounding boxes
2. The top detector bbox (if any) is wrapped in a `BBox` object and passed to
   `SpeciesNetClassifier.preprocess(pil_img, bboxes=[bbox])`
3. The model variant in use (`v4.0.2a`) is type `always_crop` — without a bbox
   the classifier falls back to a centre crop, which degrades accuracy; passing
   the detector bbox ensures the classifier sees the animal, not background
4. `SpeciesNetClassifier.predict()` returns `classifications.classes` /
   `classifications.scores`; the pipeline reads `classes[0]` and `scores[0]`
5. Bbox for the detection row and crop comes from the detector result, not the
   classifier; it is suppressed when the label is `"blank"`

**Current status**: experimental. The ensemble is commented out in
`crittercam/classifier/speciesnet.py`, not deleted. If ensemble results prove
better after further testing, re-enabling is straightforward.

**Implications**:
- `prediction_source` is no longer available (was an ensemble field); not stored
- Geofencing (`country`, `admin1_region`) was applied at the ensemble step and is
  currently inactive even if configured; the country/region args are accepted by
  `SpeciesNetAdapter.__init__` for future re-enablement
- Decision 017's field mapping is updated accordingly

---

<!-- Add new decisions below this line, incrementing the number -->
