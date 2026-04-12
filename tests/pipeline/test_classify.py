"""Tests for crittercam.pipeline.classify."""

from pathlib import Path

import pytest

from crittercam.classifier.base import Detection
from crittercam.pipeline.classify import _generate_crop, classify_pending
from crittercam.pipeline.db import reset_all, reset_errors


# ---------------------------------------------------------------------------
# Mock classifiers
# ---------------------------------------------------------------------------

class _MockClassifier:
    """Classifier that returns a predetermined list of detections."""

    model_name = 'mock'
    model_version = 'v1.0'

    def __init__(self, detections: list[Detection]) -> None:
        self._detections = detections

    def classify(self, image_path: Path) -> list[Detection]:
        return self._detections


class _FailingClassifier:
    """Classifier that always raises."""

    model_name = 'mock'
    model_version = 'v1.0'

    def classify(self, image_path: Path) -> list[Detection]:
        raise RuntimeError('model exploded')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_root(tmp_path):
    """Return a temporary data root with image directories created."""
    root = tmp_path / 'data'
    root.mkdir()
    return root


@pytest.fixture
def pending_image(db, data_root, make_jpeg):
    """Insert an image row + pending detection job; write the JPEG to disk.

    Returns a dict with image_id, job_id, filename, and image path.
    """
    img_path = data_root / 'images' / '2026' / '03' / '15' / 'IMG_001.jpg'
    make_jpeg(img_path, size=(64, 64))

    db.execute(
        '''
        INSERT INTO images (path, filename, ingested_at, file_hash, file_size)
        VALUES (?, ?, ?, ?, ?)
        ''',
        ('images/2026/03/15/IMG_001.jpg', 'IMG_001.jpg', '2026-03-15T10:00:00+00:00', 'abc123', 1024),
    )
    db.commit()
    image_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    db.execute(
        "INSERT INTO processing_jobs (image_id, job_type, status) VALUES (?, 'detection', 'pending')",
        (image_id,),
    )
    db.commit()
    job_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    return {'image_id': image_id, 'job_id': job_id, 'filename': 'IMG_001.jpg', 'path': img_path}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestClassifyPending:
    """Test the classify_pending function."""

    def test_classifies_pending_jobs(self, db, data_root, pending_image):
        # Arrange
        classifier = _MockClassifier([Detection(label='coyote', confidence=0.9, bbox=None)])

        # Act
        summary = classify_pending(data_root, db, classifier)

        # Assert
        assert summary.classified == 1
        assert summary.errors == {}

    def test_writes_detection_row(self, db, data_root, pending_image):
        # Arrange
        bbox = (0.1, 0.2, 0.3, 0.4)
        classifier = _MockClassifier([Detection(label='deer', confidence=0.85, bbox=bbox)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert
        row = db.execute('SELECT * FROM detections').fetchone()
        assert row['label'] == 'deer'
        assert row['confidence'] == pytest.approx(0.85)
        assert row['bbox_x'] == pytest.approx(0.1)
        assert row['bbox_y'] == pytest.approx(0.2)
        assert row['bbox_w'] == pytest.approx(0.3)
        assert row['bbox_h'] == pytest.approx(0.4)
        assert row['model_name'] == 'mock'
        assert row['is_active'] == 1

    def test_marks_job_as_done(self, db, data_root, pending_image):
        # Arrange
        classifier = _MockClassifier([Detection(label='fox', confidence=0.7, bbox=None)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert
        job = db.execute(
            'SELECT status, completed_at FROM processing_jobs WHERE id = ?',
            (pending_image['job_id'],),
        ).fetchone()
        assert job['status'] == 'done'
        assert job['completed_at'] is not None

    def test_records_error_on_classifier_failure(self, db, data_root, pending_image):
        # Arrange
        classifier = _FailingClassifier()

        # Act
        summary = classify_pending(data_root, db, classifier)

        # Assert
        assert 'IMG_001.jpg' in summary.errors
        job = db.execute(
            'SELECT status, error_msg FROM processing_jobs WHERE id = ?',
            (pending_image['job_id'],),
        ).fetchone()
        assert job['status'] == 'error'
        assert 'model exploded' in job['error_msg']

    def test_no_detection_row_on_failure(self, db, data_root, pending_image):
        # Act
        classify_pending(data_root, db, _FailingClassifier())

        # Assert
        count = db.execute('SELECT COUNT(*) FROM detections').fetchone()[0]
        assert count == 0

    def test_deactivates_prior_detections(self, db, data_root, pending_image):
        # Arrange — seed an existing active detection
        db.execute(
            '''
            INSERT INTO detections
                (image_id, label, confidence, model_name, is_active, created_at)
            VALUES (?, 'old_label', 0.5, 'old_model', 1, '2026-01-01T00:00:00+00:00')
            ''',
            (pending_image['image_id'],),
        )
        db.commit()
        classifier = _MockClassifier([Detection(label='bear', confidence=0.95, bbox=None)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert — old detection deactivated, new one active
        rows = db.execute(
            'SELECT label, is_active FROM detections ORDER BY id'
        ).fetchall()
        assert rows[0]['label'] == 'old_label'
        assert rows[0]['is_active'] == 0
        assert rows[1]['label'] == 'bear'
        assert rows[1]['is_active'] == 1

    def test_writes_label_assigned_by_algorithm(self, db, data_root, pending_image):
        # Arrange
        classifier = _MockClassifier([Detection(label='fox', confidence=0.8, bbox=None)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert
        row = db.execute('SELECT label_assigned_by FROM detections').fetchone()
        assert row['label_assigned_by'] == 'algorithm'

    def test_skips_image_with_human_assigned_label(self, db, data_root, pending_image):
        # Arrange — existing active detection marked as human-assigned
        db.execute(
            '''
            INSERT INTO detections
                (image_id, label, confidence, model_name, is_active,
                 label_assigned_by, created_at)
            VALUES (?, 'human corrected species', 0.0, 'human', 1,
                    'human', '2026-01-01T00:00:00+00:00')
            ''',
            (pending_image['image_id'],),
        )
        db.commit()
        classifier = _MockClassifier([Detection(label='bear', confidence=0.95, bbox=None)])

        # Act
        summary = classify_pending(data_root, db, classifier)

        # Assert — job counted as done but human label untouched
        assert summary.classified == 1
        assert summary.errors == {}
        rows = db.execute(
            'SELECT label, label_assigned_by FROM detections ORDER BY id'
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]['label'] == 'human corrected species'
        assert rows[0]['label_assigned_by'] == 'human'

    def test_skips_non_pending_jobs(self, db, data_root, pending_image):
        # Arrange — mark the job as already done
        db.execute(
            "UPDATE processing_jobs SET status = 'done' WHERE id = ?",
            (pending_image['job_id'],),
        )
        db.commit()
        classifier = _MockClassifier([Detection(label='rabbit', confidence=0.6, bbox=None)])

        # Act
        summary = classify_pending(data_root, db, classifier)

        # Assert
        assert summary.classified == 0
        assert db.execute('SELECT COUNT(*) FROM detections').fetchone()[0] == 0

    def test_blank_detection_writes_row_with_null_bbox(self, db, data_root, pending_image):
        # Arrange
        classifier = _MockClassifier([Detection(label='blank', confidence=0.99, bbox=None)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert
        row = db.execute('SELECT * FROM detections').fetchone()
        assert row['label'] == 'blank'
        assert row['bbox_x'] is None
        assert row['bbox_w'] is None

    def test_generates_crop_when_bbox_present(self, db, data_root, pending_image):
        # Arrange
        bbox = (0.1, 0.1, 0.5, 0.5)
        classifier = _MockClassifier([Detection(label='squirrel', confidence=0.75, bbox=bbox)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert — crop written and path recorded in detections table
        crop_path_str = db.execute('SELECT crop_path FROM detections').fetchone()['crop_path']
        assert crop_path_str is not None
        assert (data_root / crop_path_str).exists()

    def test_no_crop_when_no_bbox(self, db, data_root, pending_image):
        # Arrange
        classifier = _MockClassifier([Detection(label='blank', confidence=0.99, bbox=None)])

        # Act
        classify_pending(data_root, db, classifier)

        # Assert
        crop_path_str = db.execute('SELECT crop_path FROM detections').fetchone()['crop_path']
        assert crop_path_str is None


class TestResetErrors:
    """Test the reset_errors function."""

    def test_resets_errored_jobs_to_pending(self, db, data_root, pending_image):
        # Arrange — mark the job as errored
        db.execute(
            "UPDATE processing_jobs SET status = 'error', error_msg = 'boom' WHERE id = ?",
            (pending_image['job_id'],),
        )
        db.commit()

        # Act
        n = reset_errors(db, job_type='detection')

        # Assert
        assert n == 1
        job = db.execute(
            'SELECT status, error_msg, started_at FROM processing_jobs WHERE id = ?',
            (pending_image['job_id'],),
        ).fetchone()
        assert job['status'] == 'pending'
        assert job['error_msg'] is None
        assert job['started_at'] is None

    def test_does_not_reset_done_jobs(self, db, data_root, pending_image):
        # Arrange
        db.execute(
            "UPDATE processing_jobs SET status = 'done' WHERE id = ?",
            (pending_image['job_id'],),
        )
        db.commit()

        # Act
        n = reset_errors(db, job_type='detection')

        # Assert
        assert n == 0
        status = db.execute(
            'SELECT status FROM processing_jobs WHERE id = ?',
            (pending_image['job_id'],),
        ).fetchone()['status']
        assert status == 'done'

    def test_returns_count_of_reset_jobs(self, db, data_root, make_jpeg):
        # Arrange — create two errored jobs
        for i, name in enumerate(['A.jpg', 'B.jpg']):
            img_path = data_root / 'images' / '2026' / '03' / '15' / name
            make_jpeg(img_path)
            db.execute(
                'INSERT INTO images (path, filename, ingested_at, file_hash, file_size) '
                'VALUES (?, ?, ?, ?, ?)',
                (f'images/2026/03/15/{name}', name, '2026-03-15T10:00:00+00:00', f'hash{i}', 1024),
            )
            db.commit()
            image_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute(
                "INSERT INTO processing_jobs (image_id, job_type, status, error_msg) "
                "VALUES (?, 'detection', 'error', 'fail')",
                (image_id,),
            )
            db.commit()

        # Act
        n = reset_errors(db, job_type='detection')

        # Assert
        assert n == 2


class TestResetAll:
    """Test the reset_all function."""

    def test_resets_done_jobs_to_pending(self, db, data_root, pending_image):
        # Arrange
        db.execute(
            "UPDATE processing_jobs SET status = 'done' WHERE id = ?",
            (pending_image['job_id'],),
        )
        db.commit()

        # Act
        n = reset_all(db, job_type='detection')

        # Assert
        assert n == 1
        job = db.execute(
            'SELECT status, error_msg, started_at FROM processing_jobs WHERE id = ?',
            (pending_image['job_id'],),
        ).fetchone()
        assert job['status'] == 'pending'
        assert job['error_msg'] is None
        assert job['started_at'] is None

    def test_resets_errored_jobs_to_pending(self, db, data_root, pending_image):
        # Arrange
        db.execute(
            "UPDATE processing_jobs SET status = 'error', error_msg = 'boom' WHERE id = ?",
            (pending_image['job_id'],),
        )
        db.commit()

        # Act
        n = reset_all(db, job_type='detection')

        # Assert
        assert n == 1
        assert db.execute(
            'SELECT status FROM processing_jobs WHERE id = ?', (pending_image['job_id'],)
        ).fetchone()['status'] == 'pending'

    def test_does_not_reset_pending_jobs(self, db, data_root, pending_image):
        # Arrange — job is already pending (default from fixture)

        # Act
        n = reset_all(db, job_type='detection')

        # Assert
        assert n == 0

    def test_returns_total_count(self, db, data_root, make_jpeg):
        # Arrange — one done job and one error job
        for i, (name, status) in enumerate([('A.jpg', 'done'), ('B.jpg', 'error')]):
            img_path = data_root / 'images' / '2026' / '03' / '15' / name
            make_jpeg(img_path)
            db.execute(
                'INSERT INTO images (path, filename, ingested_at, file_hash, file_size) '
                'VALUES (?, ?, ?, ?, ?)',
                (f'images/2026/03/15/{name}', name, '2026-03-15T10:00:00+00:00', f'hash{i}', 1024),
            )
            db.commit()
            image_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute(
                "INSERT INTO processing_jobs (image_id, job_type, status) VALUES (?, 'detection', ?)",
                (image_id, status),
            )
            db.commit()

        # Act
        n = reset_all(db, job_type='detection')

        # Assert
        assert n == 2


class TestClassifyPendingEmpty:
    """Test edge cases for classify_pending."""

    def test_empty_detection_list_marks_job_done(self, db, data_root, pending_image):
        # Arrange — classifier returns no prediction (not a failure, just no result)
        classifier = _MockClassifier([])

        # Act
        summary = classify_pending(data_root, db, classifier)

        # Assert — job done, no detection row, no error
        assert summary.classified == 1
        assert summary.errors == {}
        assert db.execute('SELECT COUNT(*) FROM detections').fetchone()[0] == 0
        job_status = db.execute(
            'SELECT status FROM processing_jobs WHERE id = ?', (pending_image['job_id'],)
        ).fetchone()['status']
        assert job_status == 'done'


class TestGenerateCrop:
    """Test the _generate_crop function."""

    def test_returns_none_when_no_detection(self, data_root, make_jpeg):
        # Arrange
        image_rel = Path('images/2026/03/15/IMG_001.jpg')
        image_abs = data_root / image_rel
        make_jpeg(image_abs, size=(64, 64))

        # Act
        result = _generate_crop(image_abs, image_rel, data_root, detection=None, crop_padding=0.1)

        # Assert
        assert result is None

    def test_returns_none_when_bbox_is_none(self, data_root, make_jpeg):
        # Arrange
        image_rel = Path('images/2026/03/15/IMG_001.jpg')
        image_abs = data_root / image_rel
        make_jpeg(image_abs, size=(64, 64))
        detection = Detection(label='blank', confidence=0.99, bbox=None)

        # Act
        result = _generate_crop(image_abs, image_rel, data_root, detection, crop_padding=0.1)

        # Assert
        assert result is None

    def test_writes_crop_file_when_bbox_present(self, data_root, make_jpeg):
        # Arrange
        image_rel = Path('images/2026/03/15/IMG_001.jpg')
        image_abs = data_root / image_rel
        make_jpeg(image_abs, size=(200, 200))
        detection = Detection(label='deer', confidence=0.9, bbox=(0.1, 0.1, 0.5, 0.5))

        # Act
        result = _generate_crop(image_abs, image_rel, data_root, detection, crop_padding=0.0)

        # Assert
        assert result is not None
        assert (data_root / result).exists()

    def test_returns_path_relative_to_data_root(self, data_root, make_jpeg):
        # Arrange
        image_rel = Path('images/2026/03/15/IMG_001.jpg')
        image_abs = data_root / image_rel
        make_jpeg(image_abs, size=(200, 200))
        detection = Detection(label='deer', confidence=0.9, bbox=(0.1, 0.1, 0.5, 0.5))

        # Act
        result = _generate_crop(image_abs, image_rel, data_root, detection, crop_padding=0.0)

        # Assert
        assert not result.is_absolute()
        assert result == Path('derived/2026/03/15/IMG_001_det001.jpg')

    def test_padding_clamped_to_image_boundary(self, data_root, make_jpeg):
        # Arrange — bbox near the edge; large padding would go out of bounds
        image_rel = Path('images/2026/03/15/IMG_001.jpg')
        image_abs = data_root / image_rel
        make_jpeg(image_abs, size=(200, 200))
        detection = Detection(label='deer', confidence=0.9, bbox=(0.0, 0.0, 0.2, 0.2))

        # Act — should not raise even with extreme padding
        result = _generate_crop(image_abs, image_rel, data_root, detection, crop_padding=2.0)

        # Assert
        assert result is not None
        assert (data_root / result).exists()
