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
**Status**: Complete

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

### Done
- [x] `crittercam clean-db --labels <leaf> [<leaf> ...] [--dry-run]` — removes matching
      detections and their parent images from the database and deletes all associated files
      (raw image, thumbnail, crop) from disk; uses `LIKE '%;{leaf}'` to match against the
      leaf segment of the stored taxonomy string

### Completion criteria
- [x] Schema created from scratch by a single command
- [x] Migrations apply cleanly to an existing database

---

## Phase 4 — Review & query interface
**Status**: Phase 4a complete

### Scope
- Local web dashboard served by FastAPI + Uvicorn (Python backend) and React + Vite
  (frontend)
- Three-tab layout: Home, Browse, Analytics
- Phase 4a (first pass): read-only; no label correction
- Phase 4b (future): label correction interface and feedback loop to Phase 2

### Tab: Home
- Summary statistics: total images ingested, total detections, unique species seen
- Detection counts over time (bar or line chart)
- Strip of the most recent detection crops as a quick visual summary

### Tab: Browse
- Thumbnail grid of detection crops, newest first
- Sidebar filters: species (dropdown), date range (date picker)
- Click a thumbnail to open a detail panel showing the detection crop alongside the
  full image with bounding box overlay, plus metadata (species, confidence, model
  version, captured_at, temperature)

### Tab: Analytics
- Weekly detections per species line chart (past year, species with >10 detections)
- Phase 4b onwards: time-of-day activity patterns, temperature vs. activity
  correlation, and further charts as needed
- Each visualization is an independent React component backed by a dedicated FastAPI
  endpoint; new charts can be added without touching existing code

### Resolved
- Backend: FastAPI + Uvicorn (Decision 019)
- Frontend: React + Vite (Decision 019)
- Chart library: Recharts (Decision 019)
- Directory layout: React source inside `crittercam/web/ui/`; single Uvicorn process
  in production serving both API and built static files (Decision 020)
- Dev workflow: `Procfile.dev` runs Vite and Uvicorn simultaneously; Vite proxies
  `/api/*` to Uvicorn (Decision 020)
- Label correction: deferred to Phase 4b; DB schema already has `human_label` and
  `corrected_at` fields reserved
- Port: hardcoded at 8000 for now; may be moved to `config.toml` in a future pass
- Auto-open browser: yes — `crittercam serve` will call `webbrowser.open()` on start
- Pagination: page numbers (not infinite scroll) — simpler state, friendlier for
  filtered result sets where total count is known

### Done
- [x] FastAPI server (`web/server.py`) with media file serving (`GET /media/{path}`)
- [x] Shared DB connection helper (`web/api/__init__.py`)
- [x] `GET /api/stats/summary` — total images, detections, species seen
- [x] `GET /api/stats/detections_over_time` — weekly counts per species for past year
- [x] `GET /api/detections` — paginated list with species, date, and human/blank filters
- [x] `GET /api/detections/recent_by_species` — most recent detection per species
- [x] `GET /api/detections/species` — sorted list of distinct species for the filter dropdown
- [x] `GET /api/detections/{id}` — single detection with bbox, full image URL, temperature, prev/next IDs
- [x] Vite + React scaffold with `/api/*` and `/media/*` proxy to Uvicorn
- [x] `Procfile.dev` for parallel dev server startup
- [x] Three-tab layout (Home, Browse, Analytics) with tab state in `App`
- [x] `StatsBar` component — summary statistics with live data
- [x] `RecentBySpecies` component — most recent crop per species on Home tab
- [x] `DetectionsOverTime` component — Recharts line chart on Analytics tab
- [x] `DetectionGrid` component — paginated thumbnail grid
- [x] `FilterBar` component — controlled species dropdown and date range inputs
- [x] `DetailPanel` component — crop + full image with SVG bounding box overlay, metadata

### Done (continued)
- [x] `crittercam serve [--port PORT]` — loads config, warns if UI not built, opens browser,
      starts Uvicorn; serves built React app via StaticFiles mount when `dist/` is present
- [x] `crittercam build-ui` — runs `npm run build` inside `crittercam/web/ui/`

### Completion criteria (Phase 4a)
- [x] `crittercam build-ui` compiles the React app without errors
- [x] `crittercam serve` starts the dashboard; browser shows Home tab with live data
- [x] Browse tab shows detection crops; species and date filters narrow results correctly
- [x] Detail panel shows crop + full image with bounding box for any detection
- [x] Analytics tab shows weekly detections per species line chart

---

## Phase 5 — Individual re-identification
**Status**: Design complete, not started

### Scope
- For each detection crop, compute a MegaDescriptor-L-384 embedding and store
  it as a `.npy` file in `derived/`, referenced by `detections.embedding_path`
- Gallery-based nearest-neighbor matching assigns detections to individuals
  using cosine similarity; a configurable threshold controls same/new decisions
- Results stored in a new `individuals` table; `detections` gains FK and
  assignment metadata columns
- Human identity confirmations and corrections via the dashboard are permanent
  anchors that survive model upgrades (see Decision 023)
- Starting species: domestic cat

### Resolved
- Embedding model: MegaDescriptor-L-384 via `timm` + HuggingFace (Decision 021)
- Embedding storage: `.npy` flat files in `derived/`, path in DB (Decision 022)
- Matching strategy: gallery-based nearest-neighbor, not clustering (Decision 023)
- Human assignments as upgrade anchors (Decision 023)
- Schema: `individuals` table + 7 new columns on `detections` (Decision 024)
- Migration: `0002_reid_schema.sql`

### Open questions
- [ ] Similarity threshold starting value (suggested 0.75; calibrate against
      cat verification results)
- [ ] Dashboard UI for confirming/correcting/splitting individual assignments
      (Phase 4b / Phase 5b overlap)
- [ ] `crittercam reid` CLI subcommand design (flags for threshold,
      retry-errors, reclassify-all, species filter)

### Completion criteria
- [ ] `crittercam reid` processes pending embedding jobs, writes `.npy` files,
      runs gallery matching, and writes `individual_id` assignments
- [ ] Re-running on the same dataset produces no duplicate assignments
- [ ] A model upgrade re-run clears algorithm assignments, preserves human
      assignments, and re-derives identities correctly
- [ ] Detections of the same individual are linked across ingestion batches
- [ ] Per-individual detection history is queryable by `individual_id`