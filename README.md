![](assets/cirttercam_banner.jpg)

Backyard wildlife camera trap pipeline — ingestion, species identification, and local dashboard.

## Setup

### 1. Create a conda environment

```bash
conda create -n crittercam python=3.12
conda activate crittercam
```

### 2. Install the package

From the repo root:

```bash
pip install -e ".[dev]"
```

The `-e` flag installs in editable mode so code changes take effect immediately without reinstalling.

### 3. Run the tests

```bash
pytest
```

### 4. Configure crittercam

Run the setup command to set the data root (where images and the database will be stored) and initialise the database:

```bash
crittercam setup
```

You will be prompted for:
- **Data root** — path to your external drive; images and the database are stored here
- **Country code** — ISO 3166-1 alpha-3 code (e.g. `USA`) for SpeciesNet geofencing; improves accuracy by filtering out species that don't occur in your region
- **State/province** — abbreviation (e.g. `CT`) for finer-grained geofencing

The config is written to `~/.config/crittercam/config.toml` and can be updated by running `crittercam setup` again.

## Usage

### Ingest images

After offloading your SD card to a local directory, run:

```bash
crittercam ingest --source /path/to/offloaded/images
```

To override the configured data root for a single run:

```bash
crittercam ingest --source /path/to/offloaded/images --data-root /path/to/data
```

### Classify images

After ingesting, run species classification on all pending images:

```bash
crittercam classify
```

On first run, SpeciesNet will automatically download model weights (~1 GB) from Kaggle — no separate download step or credentials are required. 
Subsequent runs use the cached weights.

Each image produces:
- A detection row in the database with species label, confidence score, and bounding box
- A thumbnail at `derived/YYYY/MM/DD/<filename>_thumb.jpg`
- A padded crop at `derived/YYYY/MM/DD/<filename>_det001.jpg` (if an animal was detected)

**Overrides** — geofencing and crop padding can be adjusted per-run without changing the config:

```bash
crittercam classify --country USA --admin1-region CT --crop-padding 0.20
```
