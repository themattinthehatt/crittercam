"""Tests for crittercam.pipeline.clean."""

from pathlib import Path

import pytest

from crittercam.pipeline.clean import CleanSummary, CleanTarget, delete_targets, find_targets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed(
    db,
    data_root: Path,
    make_jpeg,
    label: str,
    file_hash: str,
    is_active: int = 1,
) -> dict:
    """Insert an image, detection, and processing_job row; write files to disk.

    Args:
        db: open database connection
        data_root: root directory for the image archive
        make_jpeg: factory fixture for creating test JPEGs
        label: detection label string
        file_hash: unique SHA-256 hash string for the image row
        is_active: is_active flag for the detection row

    Returns:
        dict with image_id, detection_id, img_path, thumb_path, crop_path
    """
    img_path = data_root / 'images' / '2026' / '01' / '01' / f'{file_hash}.jpg'
    thumb_path = data_root / 'derived' / '2026' / '01' / '01' / f'{file_hash}_thumb.jpg'
    crop_path = data_root / 'derived' / '2026' / '01' / '01' / f'{file_hash}_det001.jpg'
    make_jpeg(img_path)
    make_jpeg(thumb_path)
    make_jpeg(crop_path)

    img_rel = str(img_path.relative_to(data_root))
    thumb_rel = str(thumb_path.relative_to(data_root))
    crop_rel = str(crop_path.relative_to(data_root))

    cursor = db.execute(
        '''
        INSERT INTO images (path, filename, ingested_at, file_hash, file_size, thumb_path)
        VALUES (:path, :filename, :ingested_at, :file_hash, :file_size, :thumb_path)
        ''',
        {
            'path': img_rel,
            'filename': img_path.name,
            'ingested_at': '2026-01-01T00:00:00+00:00',
            'file_hash': file_hash,
            'file_size': 1024,
            'thumb_path': thumb_rel,
        },
    )
    image_id = cursor.lastrowid

    cursor = db.execute(
        '''
        INSERT INTO detections
            (image_id, label, confidence, crop_path, model_name, is_active, created_at)
        VALUES (:image_id, :label, :confidence, :crop_path, :model_name, :is_active, :created_at)
        ''',
        {
            'image_id': image_id,
            'label': label,
            'confidence': 0.9,
            'crop_path': crop_rel,
            'model_name': 'mock',
            'is_active': is_active,
            'created_at': '2026-01-01T00:00:00+00:00',
        },
    )
    detection_id = cursor.lastrowid

    db.execute(
        '''
        INSERT INTO processing_jobs (image_id, job_type, status, completed_at)
        VALUES (:image_id, 'detection', 'done', :completed_at)
        ''',
        {'image_id': image_id, 'completed_at': '2026-01-01T00:00:00+00:00'},
    )
    db.commit()

    return {
        'image_id': image_id,
        'detection_id': detection_id,
        'img_path': img_path,
        'thumb_path': thumb_path,
        'crop_path': crop_path,
    }


@pytest.fixture
def data_root(tmp_path):
    """Return a temporary data root directory."""
    root = tmp_path / 'data'
    root.mkdir()
    return root


# ---------------------------------------------------------------------------
# find_targets
# ---------------------------------------------------------------------------

class TestFindTargets:
    """Test the find_targets function."""

    def test_find_targets_matches_blank_by_leaf(self, db, data_root, make_jpeg):
        # Arrange — blank is stored with a UUID prefix like all other labels
        row = _seed(db, data_root, make_jpeg, label='abc123;;;;;blank', file_hash='b1')

        # Act
        targets = find_targets(db, ['blank'])

        # Assert
        assert len(targets) == 1
        assert targets[0].detection_id == row['detection_id']

    def test_find_targets_matches_hierarchical_label_by_leaf(self, db, data_root, make_jpeg):
        # Arrange — label stored as full taxonomy string; user passes only the leaf
        row = _seed(
            db, data_root, make_jpeg,
            label='animalia;chordata;mammalia;primates;hominidae;homo;homo sapiens',
            file_hash='h1',
        )

        # Act
        targets = find_targets(db, ['homo sapiens'])

        # Assert
        assert len(targets) == 1
        assert targets[0].detection_id == row['detection_id']

    def test_find_targets_does_not_match_non_leaf_segment(self, db, data_root, make_jpeg):
        # Arrange — 'mammalia' appears in the hierarchy but is not the leaf
        _seed(
            db, data_root, make_jpeg,
            label='animalia;chordata;mammalia;carnivora;canidae;canis;canis latrans',
            file_hash='c1',
        )

        # Act — searching for 'mammalia' should not match
        targets = find_targets(db, ['mammalia'])

        # Assert
        assert targets == []

    def test_find_targets_ignores_non_matching_labels(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;animalia;chordata;mammalia;deer', file_hash='d1')

        # Act
        targets = find_targets(db, ['human', 'blank'])

        # Assert
        assert targets == []

    def test_find_targets_ignores_inactive_detections(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;;;;;blank', file_hash='b1', is_active=0)

        # Act
        targets = find_targets(db, ['blank'])

        # Assert
        assert targets == []

    def test_find_targets_matches_multiple_labels(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;homo sapiens', file_hash='h1')
        _seed(db, data_root, make_jpeg, label='abc123;;;;;blank', file_hash='b1')
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;odocoileus virginianus', file_hash='d1')

        # Act
        targets = find_targets(db, ['homo sapiens', 'blank'])

        # Assert
        assert len(targets) == 2

    def test_find_targets_returns_empty_for_empty_labels(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;;;;;blank', file_hash='b1')

        # Act
        targets = find_targets(db, [])

        # Assert
        assert targets == []

    def test_find_targets_includes_paths(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;;;;;blank', file_hash='b1')

        # Act
        targets = find_targets(db, ['blank'])

        # Assert
        assert targets[0].image_path is not None
        assert targets[0].thumb_path is not None
        assert targets[0].crop_path is not None


# ---------------------------------------------------------------------------
# delete_targets
# ---------------------------------------------------------------------------

class TestDeleteTargets:
    """Test the delete_targets function."""

    def test_delete_targets_removes_detection_row(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert db.execute('SELECT COUNT(*) FROM detections').fetchone()[0] == 0

    def test_delete_targets_removes_image_row(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert db.execute('SELECT COUNT(*) FROM images').fetchone()[0] == 0

    def test_delete_targets_removes_processing_jobs(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert db.execute('SELECT COUNT(*) FROM processing_jobs').fetchone()[0] == 0

    def test_delete_targets_deletes_crop_file(self, db, data_root, make_jpeg):
        # Arrange
        row = _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert not row['crop_path'].exists()

    def test_delete_targets_deletes_thumbnail_file(self, db, data_root, make_jpeg):
        # Arrange
        row = _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert not row['thumb_path'].exists()

    def test_delete_targets_deletes_raw_image_file(self, db, data_root, make_jpeg):
        # Arrange
        row = _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert not row['img_path'].exists()

    def test_delete_targets_preserves_non_matching_rows(self, db, data_root, make_jpeg):
        # Arrange
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        _seed(db, data_root, make_jpeg, label='abc123;animalia;...;deer', file_hash='d1')
        targets = find_targets(db, ['human'])

        # Act
        delete_targets(data_root, db, targets)

        # Assert
        assert db.execute('SELECT COUNT(*) FROM images').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM detections').fetchone()[0] == 1
        remaining = db.execute('SELECT label FROM detections').fetchone()
        assert remaining['label'].endswith(';deer')

    def test_delete_targets_also_removes_inactive_detections(self, db, data_root, make_jpeg):
        # Arrange — seed a row, then add a second inactive detection for the same image
        row = _seed(db, data_root, make_jpeg, label='abc123;animalia;...;human', file_hash='h1')
        db.execute(
            '''
            INSERT INTO detections (image_id, label, confidence, model_name, is_active, created_at)
            VALUES (:image_id, 'human', 0.7, 'old_model', 0, '2025-01-01T00:00:00+00:00')
            ''',
            {'image_id': row['image_id']},
        )
        db.commit()
        targets = find_targets(db, ['human'])

        # Act
        summary = delete_targets(data_root, db, targets)

        # Assert — both detection rows deleted
        assert db.execute('SELECT COUNT(*) FROM detections').fetchone()[0] == 0
        assert summary.detections == 2

    def test_delete_targets_counts_missing_files(self, db, data_root, make_jpeg):
        # Arrange — remove the crop before deletion to simulate a missing file
        row = _seed(db, data_root, make_jpeg, label='abc123;;;;;blank', file_hash='b1')
        row['crop_path'].unlink()
        targets = find_targets(db, ['blank'])

        # Act
        summary = delete_targets(data_root, db, targets)

        # Assert
        assert summary.files_missing == 1
        assert summary.crops_deleted == 0
        assert summary.thumbnails_deleted == 1
        assert summary.raw_images_deleted == 1

    def test_delete_targets_returns_empty_summary_for_no_targets(self, db, data_root, make_jpeg):
        # Act
        summary = delete_targets(data_root, db, [])

        # Assert
        assert summary.detections == 0
        assert summary.images == 0
        assert summary.raw_images_deleted == 0
        assert summary.thumbnails_deleted == 0
        assert summary.crops_deleted == 0
        assert summary.files_missing == 0
