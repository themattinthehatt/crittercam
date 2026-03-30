# Project Phases — Status Tracker

## Phase 1 — Ingestion pipeline
**Status**: Complete

### Scope
- Accept a source directory (manually pointed at offloaded SD card contents)
- Compute SHA-256 hash of each JPEG; skip if hash already exists in `images` table
- Copy new files into `<data_root>/images/YYYY/MM/DD/`
- Extract EXIF metadata (timestamp, filename, size) at ingest time
- Generate a full-image thumbnail (max 320px) immediately after copying; write to `derived/YYYY/MM/DD/`
- Insert row into `images` table, including `thumb_path`
- Insert `processing_jobs` row (job_type='detection', status='pending') for each new image

### Resolved
- Deduplication key: SHA-256 file hash (Decision 009)
- Pipeline is batch-triggered (manual), not a continuous watcher (Decision 005)
- Paths stored relative to data_root (Decision 010)

### Open questions
- [ ] How to detect SD card mount reliably on this OS?

### Done
- [x] `crittercam setup` — prompts for data_root, writes config, initialises database
- [x] `crittercam ingest --source PATH` — finds JPEGs, deduplicates by SHA-256, copies to archive, writes DB rows, enqueues detection jobs
- [x] EXIF extraction — timestamp, dimensions, camera make/model, temperature (Browning UserComment)
- [x] mtime fallback when EXIF timestamp is absent
- [x] Destination collision detection (different hash, same filename + date → error, not silent overwrite)
- [x] Idempotency verified — re-running on the same source produces no duplicates
- [x] Thumbnail generation at ingest time (max 320px, `derived/YYYY/MM/DD/<stem>_thumb.jpg`); path recorded in `images.thumb_path`

### Completion criteria
- [x] Point CLI at source directory → images appear in `images/` tree, organized by date
- [x] Re-running on the same source adds no duplicates
- [x] Each new image produces a pending detection job in `processing_jobs`
- [x] Each new image has a thumbnail in `derived/` and `thumb_path` recorded in DB

---

## Phase 2 — Processing & species ID
**Status**: Complete

### Scope
- Batch worker reads pending detection jobs from `processing_jobs`
- Runs classifier (SpeciesNet) via the swappable classifier interface
- Writes detection rows to `detections` table; marks prior rows `is_active = 0` if re-running
- Generates detection crop (padded bbox) per detection
- Derived asset paths stored relative to data_root
- Marks `processing_jobs` row as done (or error)

### Resolved
- Classifier: SpeciesNet (google/cameratrapai), run locally (Decisions 002, 016)
- One detection row per image; top SpeciesNet bbox used for crop (Decision 017)
- Bounding boxes stored as (x, y, w, h) normalized — SpeciesNet's native format
- Geofencing via country + admin1_region in config (country='USA', admin1_region='CT')
- `is_active` flag distinguishes current model run from prior runs (Decision 012)
- `processing_jobs` tracks state; results live in `detections` (Decision 011)
- Crop padding configurable via `--crop-padding` CLI flag (default 0.15)

### Done
- [x] `Classifier` Protocol + `Detection` dataclass (`classifier/base.py`)
- [x] `SpeciesNetAdapter` wrapping detector + classifier + ensemble (`classifier/speciesnet.py`); handles MPO/non-RGB images via PIL convert
- [x] `classify_pending()` — processes all pending jobs, writes detection rows, generates crops
- [x] `reset_errors()` / `reset_all()` — retry errored or all jobs
- [x] `crittercam classify` CLI subcommand with `--country`, `--admin1-region`, `--crop-padding`, `--retry-errors`, `--reclassify-all` overrides
- [x] `crittercam setup` updated to prompt for country and admin1_region
- [x] Country validation against full ISO 3166-1 alpha-3 code list
- [x] Detection crop generation with configurable padding (`derived/YYYY/MM/DD/<stem>_det001.jpg`); path recorded in `detections.crop_path`

### Completion criteria
- [x] Pending detection jobs → species label + confidence score in `detections`
- [x] Crops written to `derived/` tree and referenced in DB
- [x] Re-running with a new model produces new rows; old rows marked inactive

---

## Phase 3 — Storage layer
**Status**: In progress

### Scope
- SQLite schema implementation (images, detections, processing_jobs)
- Migration infrastructure
- CSV / JSON export scripts

### Resolved
- Schema designed: see DESIGN.md for full DDL
- Paths stored relative to data_root; database lives on external drive with images (Decision 010)
- No BLOBs; derived assets on disk, referenced by path (Decision 006)
- Migration tool: hand-rolled versioned SQL scripts (Decision 015)

### Done
- [x] Schema designed and implemented (`0001_initial_schema.sql`)
- [x] Migration runner (`pipeline/db.py`) — applies pending migrations in order, idempotent
- [x] `crittercam setup` runs migrations on first run and on re-run

### Remaining
- [ ] CSV / JSON export scripts

### Completion criteria
- [x] Schema created from scratch by a single command
- [x] Migrations apply cleanly to an existing database
- [ ] All detections queryable by species, date, confidence
- [ ] Full dataset exportable to CSV in one command

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
- [ ] Browse all detections with thumbnail + metadata
- [ ] Correct a wrong label in under 3 clicks
- [ ] Corrections are clearly distinguished from AI-generated labels in the DB

---

## Phase 5 — Individual re-identification
**Status**: Not started

### Scope
- Given detections of the same species, identify whether they depict the same individual
- Build and maintain per-individual identity records linked to detection rows
- Support manual confirmation and correction of identity assignments

### Open questions
- [ ] Which re-ID approach? (embedding similarity, dedicated re-ID model, manual clustering)
- [ ] What species to target first? (deer and coyote are likely highest-volume)
- [ ] How to represent identity in the DB — new `individuals` table, or field on `detections`?
- [ ] Confidence threshold for automatic assignment vs. flagging for human review

### Completion criteria
- [ ] Detections of the same individual are linked across sessions
- [ ] Identity assignments are queryable and correctable via the interface
- [ ] Per-individual activity history is browsable
