-- initial schema: images, detections, processing_jobs

CREATE TABLE images (
    id          INTEGER PRIMARY KEY,
    path        TEXT    NOT NULL UNIQUE,
    filename    TEXT    NOT NULL,
    captured_at TEXT,
    ingested_at TEXT    NOT NULL,
    file_hash   TEXT    NOT NULL UNIQUE,
    file_size   INTEGER NOT NULL,
    thumb_path  TEXT
);

CREATE TABLE detections (
    id            INTEGER PRIMARY KEY,
    image_id      INTEGER NOT NULL REFERENCES images(id),
    label         TEXT    NOT NULL,
    confidence    REAL    NOT NULL,
    bbox_x1       REAL,
    bbox_y1       REAL,
    bbox_x2       REAL,
    bbox_y2       REAL,
    crop_path     TEXT,
    model_name    TEXT    NOT NULL,
    model_version TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL,
    human_label   TEXT,
    corrected_at  TEXT
);

CREATE TABLE processing_jobs (
    id           INTEGER PRIMARY KEY,
    image_id     INTEGER REFERENCES images(id),
    detection_id INTEGER REFERENCES detections(id),
    job_type     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'pending',
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
