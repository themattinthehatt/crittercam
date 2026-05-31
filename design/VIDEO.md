# Video Support — Implementation Plan

Adds mp4/avi video ingestion and classification to the pipeline, with UI updates to the
detail modal. Three groups of work: schema + ingestion, classification, and UI.

For design rationale see Decision 029. For schema reference see DESIGN.md.

---

## Group A — Schema and video utilities

**Step 1: Migration**
New file `crittercam/pipeline/migrations/0003_video_schema.sql`:
```sql
ALTER TABLE media ADD COLUMN thumb_frame_idx INTEGER NOT NULL DEFAULT 0;
ALTER TABLE media ADD COLUMN duration_s REAL;
```
`thumb_frame_idx` defaults to 0 for all existing image rows (correct: the thumbnail is always
the first frame for images). `duration_s` is NULL for images.

---

**Step 2: `crittercam/pipeline/video.py`**

New module; all video I/O lives here, imported by both ingest and classify.

```
VideoMeta          dataclass: width, height, frame_count, fps, duration_s
get_video_meta     (path: Path) -> VideoMeta                 — cv2.VideoCapture properties
extract_frame      (path: Path, frame_idx: int) -> Image     — single frame as PIL Image (RGB)
frame_indices_uniform  (frame_count: int, n: int) -> list[int]   — see sampling rules below
hash_first_frame   (path: Path) -> str                       — frame 0 → JPEG bytes → SHA-256 hex
save_frame_as_thumbnail  (path: Path, frame_idx: int, dest: Path, max_size: int = 320) -> None
```

**`frame_indices_uniform` rules** (in priority order):
1. `frame_count <= n` → return `list(range(frame_count))` (classify every frame)
2. `n == 1` → return `[0]`
3. Otherwise → `[round(i * (frame_count - 1) / (n - 1)) for i in range(n)]`
   — always includes first and last frame; no duplicate indices

**`hash_first_frame`**: extract frame 0, encode to JPEG bytes in-memory (no temp file),
return `hashlib.sha256(jpeg_bytes).hexdigest()`. Consistent across runs for the same video.

---

**Step 3: Tests — `tests/pipeline/test_video.py`**

Add a `sample_video_path` fixture to `tests/pipeline/conftest.py` that generates a small
synthetic mp4 (10 frames, 320×240, solid colour) using `cv2.VideoWriter` into `tmp_path`.

Test classes:

| Class | Scenarios |
|---|---|
| `TestGetVideoMeta` | correct width, height, frame_count, fps, duration_s |
| `TestFrameIndicesUniform` | n=1 → [0]; n < frame_count → evenly spaced, no duplicates; n = frame_count → every frame; n > frame_count → every frame |
| `TestHashFirstFrame` | returns 64-char hex; same call twice returns same value |
| `TestSaveFrameAsThumbnail` | produces a valid JPEG with both dimensions ≤ max_size |

---

## Group B — Ingestion

**Step 4: `crittercam/pipeline/ingest.py`**

Changes:
- Add `_VIDEO_SUFFIXES = {'.mp4', '.avi'}`
- Rename `_find_jpegs` → `_find_media_files`; yield JPEG and video suffixes
- Add `_hash_video_file(path: Path) -> str` — thin wrapper around `video.hash_first_frame()`
- Add `_collect_video_metadata(path: Path) -> dict` — calls `video.get_video_meta()` for
  `width`, `height`, `duration_s`; `captured_at` from mtime fallback (no EXIF for video);
  `temperature_c = None`; `media_type = 'video'`
- In the main `ingest()` loop, branch on suffix:
  - **Image**: existing path; now explicitly inserts `media_type='image'`, `thumb_frame_idx=0`,
    `duration_s=None`
  - **Video**: `_hash_video_file`, `_collect_video_metadata`, `video.save_frame_as_thumbnail`
    for the initial thumbnail; inserts `media_type='video'`, `thumb_frame_idx=0`, `duration_s`
- Update the INSERT statement to include the three new columns for all media types

Note: the initial video thumbnail is always frame 0. It will be overwritten by the classify
phase once the representative frame is known.

---

**Step 5: `pyproject.toml`**

Verify `opencv-python-headless` is available as a transitive dependency of SpeciesNet. If not
present in the environment, add it explicitly:
```toml
"opencv-python-headless",
```

---

**Step 6: Ingest tests — `tests/pipeline/test_ingest.py`**

Add `TestIngestVideo` class using the `sample_video_path` fixture:
- Verifies `media_type='video'` in the inserted row
- Verifies `thumb_frame_idx=0`
- Verifies `duration_s` is a positive float
- Verifies hash was computed from the first frame (not raw file bytes)
- Verifies thumbnail JPEG was written to `derived/YYYY/MM/DD/<stem>_thumb.jpg`
- Verifies a `processing_jobs` row was created with `job_type='detection'`
- Re-running on the same video skips it (idempotency)

---

## Group C — Classification

**Step 7: Voting helper — `crittercam/pipeline/classify.py`**

New private function `_select_winning_detection(detections: list[Detection]) -> Detection`:

```
1. Partition: blank (leaf segment == 'blank') vs. non-blank
2. If all blank → return highest-confidence blank
3. Otherwise: count non-blank label occurrences
4. Find label(s) with max vote count
5. Tie on count → pick label with highest SUM(confidence) across its frames
6. Return the Detection for the winning label with the highest individual confidence
   (this is the representative frame: its bbox and confidence go in the detections row)
```

The leaf segment is the last semicolon-delimited field of the taxonomy label string,
consistent with all other label handling in the codebase.

---

**Step 8: Video classify path — `crittercam/pipeline/classify.py`**

Add `video_frames: int = 5` parameter to `classify_pending`.

Update the pending query to also select `i.media_type, i.thumb_path`.

Add private `_classify_video(conn, job, classifier, data_root, crop_padding, n_frames)`:
1. `video.get_video_meta(video_path)` → frame count
2. `video.frame_indices_uniform(frame_count, n_frames)` → list of frame indices
3. Open `tempfile.TemporaryDirectory()` for working frames
4. For each index: `video.extract_frame()`, save as JPEG to tempdir, run
   `classifier.classify()`; on per-frame failure, log a warning and continue
5. If all frames failed → raise (triggers existing error handling in `classify_pending`)
6. `_select_winning_detection(frame_detections)` → representative Detection + frame index
7. `_generate_crop(image_path=temp_frame_path, ...)` — no changes to `_generate_crop` itself
8. Overwrite thumbnail: `video.save_frame_as_thumbnail(video_path, winning_frame_idx,
   data_root / thumb_path)`; `UPDATE media SET thumb_frame_idx = :idx WHERE id = :media_id`
9. Insert detection row (identical schema to image path)

Branch in `classify_pending`: `if job['media_type'] == 'video'` → `_classify_video`;
else → existing image path (unchanged).

---

**Step 9: CLI — `crittercam/cli/cmd_classify.py`**

Add `--video-frames INT` argument (default 5). Pass through to `classify_pending`.

---

**Step 10: Classification tests — `tests/pipeline/test_classify.py`**

New class `TestSelectWinningDetection`:

| Scenario | Expected result |
|---|---|
| Single detection | returns it unchanged |
| All blank | highest-confidence blank returned |
| One non-blank among blanks | non-blank wins regardless of count |
| Clear non-blank plurality | plurality winner returned |
| Tie by vote count | label with higher total confidence wins |
| Tie both by count and total confidence | highest single-frame confidence breaks tie |

New class `TestClassifyVideo`: mocked classifier + `sample_video_path` fixture:
- Detection row inserted with correct label and confidence
- Crop written to `derived/`
- `media.thumb_frame_idx` updated to a non-zero frame (given 10-frame synthetic video with N=5)
- Thumbnail file overwritten with new content

---

## Group D — UI

**Step 11: API — `crittercam/web/api/detections.py`**

In `GET /api/detections/{id}`:
- Add `i.media_type, i.thumb_path` to the SELECT
- Rename `image_url` → `media_url` in the response dict (points to original file for both
  images and videos; the frontend branches on `media_type` to decide how to render it)
- Add `thumb_url: f'/media/{row["thumb_path"]}'` (the thumbnail JPEG; used for the
  right-panel image + bbox overlay for both images and videos)
- Add `media_type: row['media_type']`

`GET /api/detections` (list) does not need changes — the grid uses only `crop_url`.

---

**Step 12: DetectionModal — `crittercam/web/ui/src/components/DetectionModal.jsx`**

Update `detection.image_url` → `detection.media_url` everywhere.

**Left panel** (currently shows the crop):
```jsx
{detection.media_type === 'video'
  ? <video controls src={detection.media_url}
           className="max-w-full max-h-full object-contain rounded" />
  : detection.crop_url
      ? <img className="max-w-full max-h-full object-contain rounded"
             src={detection.crop_url} alt={label} />
      : <span className="text-sm text-base-content/40">no crop</span>
}
```

**Right panel** (currently shows full image with bbox overlay):
- Change `src={detection.image_url}` to:
  - video: `src={detection.thumb_url}` (the representative frame; bbox coords are valid here
    because the bbox was computed from this exact frame, and the SVG uses normalized 0–1 coords)
  - image: `src={detection.media_url}` (full image; same as before, just renamed field)

Nav arrows, favorite, delete, and edit mode are unchanged.

---

**Step 13: Stories — `crittercam/web/ui/src/components/DetectionModal.stories.jsx`**

- Update all existing stories: rename `image_url` → `media_url` in args
- Add `VideoDetection` story:
  ```js
  export const VideoDetection = {
    args: {
      ...Default.args,
      media_type: 'video',
      media_url: 'https://www.w3schools.com/html/mov_bbb.mp4',  // public placeholder
      thumb_url: 'https://placehold.co/400x300',
    },
  }
  ```

---

## File summary

| File | Status |
|---|---|
| `crittercam/pipeline/migrations/0003_video_schema.sql` | new |
| `crittercam/pipeline/video.py` | new |
| `tests/pipeline/test_video.py` | new |
| `crittercam/pipeline/ingest.py` | modified |
| `crittercam/pipeline/classify.py` | modified |
| `crittercam/cli/cmd_classify.py` | modified |
| `crittercam/web/api/detections.py` | modified |
| `crittercam/web/ui/src/components/DetectionModal.jsx` | modified |
| `crittercam/web/ui/src/components/DetectionModal.stories.jsx` | modified |
| `tests/pipeline/test_ingest.py` | modified |
| `tests/pipeline/test_classify.py` | modified |
| `tests/pipeline/conftest.py` | modified |
| `pyproject.toml` | modified if cv2 not already present |

Implementation order: Steps 1 → 2 → 3 (schema + utilities, fully testable in isolation) →
4 → 5 → 6 (ingestion, testable end-to-end without a classifier) →
7 → 8 → 9 → 10 (classification, testable with mocked classifier) →
11 → 12 → 13 (UI, testable in Storybook then browser).
