# Project Phases — Status Tracker

## Phase 1 — Ingestion pipeline
**Status**: Not started

### Scope
- Accept a source directory (manually pointed at offloaded SD card contents)
- Compute SHA-256 hash of each JPEG; skip if hash already exists in `images` table
- Copy new files into `<data_root>/images/YYYY/MM/DD/`
- Extract EXIF metadata (timestamp, filename, size) at ingest time
- Insert row into `images` table
- Insert `processing_jobs` row (job_type='detection', status='pending') for each new image

### Resolved
- Deduplication key: SHA-256 file hash (Decision 009)
- Pipeline is batch-triggered (manual), not a continuous watcher (Decision 005)
- Paths stored relative to data_root (Decision 010)

### Open questions
- [ ] How to detect SD card mount reliably on this OS?

### Completion criteria
- Point CLI at source directory → images appear in `images/` tree, organized by date
- Re-running on the same source adds no duplicates
- Each new image produces a pending detection job in `processing_jobs`

---

## Phase 2 — Processing & species ID
**Status**: Not started

### Scope
- Batch worker reads pending detection jobs from `processing_jobs`
- Runs classifier (MegaDetector) via the swappable classifier interface
- Writes detection rows to `detections` table; marks prior rows `is_active = 0` if re-running
- Generates derived assets: full-image thumbnail, padded crop per detection
- Derived asset paths stored relative to data_root
- Marks `processing_jobs` row as done (or error)

### Resolved
- Classifier is a swappable component behind a clean interface (Decision 002)
- Images with no detections: no detection rows inserted; derived: thumbnail only
- `is_active` flag distinguishes current model run from prior runs (Decision 012)
- `processing_jobs` tracks state; results live in `detections` (Decision 011)

### Open questions
- [ ] Run MegaDetector locally or call an API?

### Completion criteria
- Pending detection jobs → species label + confidence score in `detections` within ~60 seconds
- Images with no detection have no detection rows (derivable at query time)
- Re-running with a new model produces new rows; old rows marked inactive

---

## Phase 3 — Storage layer
**Status**: Not started

### Scope
- SQLite schema implementation (images, detections, processing_jobs)
- Migration infrastructure
- CSV / JSON export scripts

### Resolved
- Schema designed: see DESIGN.md for full DDL
- Paths stored relative to data_root; database lives on external drive with images (Decision 010)
- No BLOBs; derived assets on disk, referenced by path (Decision 006)

### Open questions
- [ ] Migration tool: Alembic vs hand-rolled versioned scripts?

### Completion criteria
- Schema created from scratch by a single command
- Migrations apply cleanly to an existing database
- All detections queryable by species, date, confidence
- Full dataset exportable to CSV in one command

---

## Phase 4 — Review & query interface
**Status**: Not started

### Scope
- Local web dashboard (browse images + detections)
- Filter / search UI
- Label correction interface
- Correction feedback loop to Phase 2

### Open questions
- [ ] Web framework choice
- [ ] How does a correction get stored — override field in DB, or new record?
- [ ] Should corrections trigger re-processing or just update the label?

### Completion criteria
- Browse all detections with thumbnail + metadata
- Correct a wrong label in under 3 clicks
- Corrections are clearly distinguished from AI-generated labels in the DB
