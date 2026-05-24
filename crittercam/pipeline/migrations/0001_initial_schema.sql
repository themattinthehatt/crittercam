-- initial schema: deployments, media, detections, processing_jobs

CREATE TABLE deployments (
    id              INTEGER PRIMARY KEY,
    deployment_name TEXT,
    location_id     INTEGER,
    location_name   TEXT,
    camera_make     TEXT,
    camera_model    TEXT
);

CREATE TABLE media (
    id            INTEGER PRIMARY KEY,
    deployment_id INTEGER REFERENCES deployments(id),
    captured_at   TEXT,
    path          TEXT    NOT NULL UNIQUE,
    filename      TEXT    NOT NULL,
    media_type    TEXT    NOT NULL DEFAULT 'image',
    width         INTEGER,
    height        INTEGER,
    ingested_at   TEXT    NOT NULL,
    file_hash     TEXT    NOT NULL UNIQUE,
    file_size     INTEGER NOT NULL,
    temperature_c REAL,
    thumb_path    TEXT,
    favorite      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE detections (
    id                INTEGER PRIMARY KEY,
    media_id          INTEGER NOT NULL REFERENCES media(id),
    crop_path         TEXT,
    bbox_x            REAL,
    bbox_y            REAL,
    bbox_w            REAL,
    bbox_h            REAL,
    label             TEXT    NOT NULL,
    confidence        REAL    NOT NULL,
    label_assigned_at TEXT,
    label_assigned_by TEXT    NOT NULL DEFAULT 'algorithm',
    model_name        TEXT    NOT NULL,
    model_version     TEXT,
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT    NOT NULL
);

CREATE TABLE processing_jobs (
    id           INTEGER PRIMARY KEY,
    media_id     INTEGER REFERENCES media(id),
    detection_id INTEGER REFERENCES detections(id),
    job_type     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'pending',
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
