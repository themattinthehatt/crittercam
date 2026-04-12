-- migration 0002 — individual re-identification schema
--
-- adds the individuals table and extends detections with embedding
-- provenance, identity assignment, and assignment metadata columns.
-- see decisions 021-024.

CREATE TABLE individuals (
    id           INTEGER PRIMARY KEY,
    species_leaf TEXT    NOT NULL,
    nickname     TEXT,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

ALTER TABLE detections ADD COLUMN embedding_path         TEXT;
ALTER TABLE detections ADD COLUMN reid_model_name        TEXT;
ALTER TABLE detections ADD COLUMN reid_model_version     TEXT;
ALTER TABLE detections ADD COLUMN individual_id          INTEGER REFERENCES individuals(id);
ALTER TABLE detections ADD COLUMN individual_similarity  REAL;
ALTER TABLE detections ADD COLUMN individual_assigned_by TEXT;
ALTER TABLE detections ADD COLUMN individual_assigned_at TEXT;

CREATE INDEX idx_detections_individual_id
    ON detections(individual_id)
    WHERE individual_id IS NOT NULL;