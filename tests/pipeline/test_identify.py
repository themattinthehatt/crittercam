"""Tests for crittercam.pipeline.identify."""

from pathlib import Path

import numpy as np
import pytest

from crittercam.identifier.base import Embedding
from crittercam.pipeline.identify import (
    IdentifySummary,
    _build_species_filter,
    _get_gallery,
    _next_individual_id,
    enqueue_pending,
    identify_pending,
    match_pending,
    merge_individuals,
    reidentify_all,
    reset_assignments,
)


# ---------------------------------------------------------------------------
# Mock identifier
# ---------------------------------------------------------------------------

class _MockIdentifier:
    """Identifier that returns a predetermined unit-normalised vector."""

    model_name = 'mock'
    model_version = 'v0'

    def __init__(self, vector: np.ndarray | None = None, dim: int = 4) -> None:
        if vector is not None:
            self._vector = vector.astype(np.float32)
        else:
            v = np.ones(dim, dtype=np.float32)
            self._vector = v / np.linalg.norm(v)

    def embed(self, image_path: Path) -> Embedding:
        return Embedding(vector=self._vector.copy())


class _FailingIdentifier:
    """Identifier that always raises."""

    model_name = 'mock'
    model_version = 'v0'

    def embed(self, image_path: Path) -> Embedding:
        raise RuntimeError('identifier exploded')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit(v: list[float]) -> np.ndarray:
    """Return a unit-normalised float32 array."""
    arr = np.array(v, dtype=np.float32)
    return arr / np.linalg.norm(arr)


def _insert_image(db, data_root, name='IMG_001.jpg', date='2026/03/15', make_file=True):
    """Insert an images row and optionally create the JPEG on disk."""
    path_rel = f'images/{date}/{name}'
    img_abs = data_root / path_rel
    if make_file:
        img_abs.parent.mkdir(parents=True, exist_ok=True)
        from PIL import Image as PILImage
        PILImage.new('RGB', (64, 64)).save(img_abs, format='JPEG')
    db.execute(
        'INSERT INTO images (path, filename, ingested_at, file_hash, file_size)'
        ' VALUES (:path, :filename, :ingested_at, :file_hash, :file_size)',
        {
            'path': path_rel,
            'filename': name,
            'ingested_at': '2026-03-15T10:00:00+00:00',
            'file_hash': name,
            'file_size': 1024,
        },
    )
    db.commit()
    return db.execute('SELECT last_insert_rowid()').fetchone()[0]


def _insert_detection(
    db,
    data_root,
    image_id,
    label='abc;animalia;chordata;mammalia;carnivora;felidae;felis;felis catus',
    with_crop=True,
    name='IMG_001',
    date='2026/03/15',
):
    """Insert a detections row and optionally create a crop file."""
    crop_rel = None
    if with_crop:
        crop_rel = f'derived/{date}/{name}_det001.jpg'
        crop_abs = data_root / crop_rel
        crop_abs.parent.mkdir(parents=True, exist_ok=True)
        from PIL import Image as PILImage
        PILImage.new('RGB', (32, 32)).save(crop_abs, format='JPEG')

    db.execute(
        '''
        INSERT INTO detections
            (image_id, label, confidence, crop_path, model_name, is_active, created_at)
        VALUES (:image_id, :label, :confidence, :crop_path, :model_name, 1, :created_at)
        ''',
        {
            'image_id': image_id,
            'label': label,
            'confidence': 0.9,
            'crop_path': crop_rel,
            'model_name': 'speciesnet',
            'created_at': '2026-03-15T10:00:00+00:00',
        },
    )
    db.commit()
    return db.execute('SELECT last_insert_rowid()').fetchone()[0]


def _insert_individual(db, species_leaf='felis catus'):
    """Insert an individuals row and return its id."""
    db.execute(
        'INSERT INTO individuals (species_leaf, created_at, updated_at)'
        ' VALUES (:sl, :ca, :ua)',
        {'sl': species_leaf, 'ca': '2026-03-15T10:00:00+00:00', 'ua': '2026-03-15T10:00:00+00:00'},
    )
    db.commit()
    return db.execute('SELECT last_insert_rowid()').fetchone()[0]


def _write_embedding(data_root, crop_rel: str, vector: np.ndarray) -> str:
    """Write a .npy embedding alongside the crop; return the relative path."""
    crop_path = Path(crop_rel)
    emb_rel = str(crop_path.parent / f'{crop_path.stem}_emb.npy')
    emb_abs = data_root / emb_rel
    emb_abs.parent.mkdir(parents=True, exist_ok=True)
    np.save(emb_abs, vector)
    return emb_rel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_root(tmp_path):
    """Return a temporary data root directory."""
    root = tmp_path / 'data'
    root.mkdir()
    return root


@pytest.fixture
def detection(db, data_root):
    """Insert one image + active detection with a crop; return a dict of ids."""
    image_id = _insert_image(db, data_root)
    detection_id = _insert_detection(db, data_root, image_id)
    return {'image_id': image_id, 'detection_id': detection_id}


# ---------------------------------------------------------------------------
# TestEnqueuePending
# ---------------------------------------------------------------------------

class TestEnqueuePending:
    """Test the enqueue_pending function."""

    def test_creates_job_for_detection_with_crop(self, db, data_root, detection):
        # Act
        n = enqueue_pending(db)

        # Assert
        assert n == 1
        job = db.execute(
            "SELECT * FROM processing_jobs WHERE detection_id = :id AND job_type = 'embedding'",
            {'id': detection['detection_id']},
        ).fetchone()
        assert job is not None
        assert job['status'] == 'pending'

    def test_skips_detection_without_crop(self, db, data_root):
        # Arrange
        image_id = _insert_image(db, data_root)
        _insert_detection(db, data_root, image_id, with_crop=False)

        # Act
        n = enqueue_pending(db)

        # Assert
        assert n == 0

    def test_skips_detection_with_existing_job(self, db, data_root, detection):
        # Arrange — enqueue once
        enqueue_pending(db)

        # Act — enqueue again
        n = enqueue_pending(db)

        # Assert — second call adds nothing
        assert n == 0
        count = db.execute(
            "SELECT COUNT(*) FROM processing_jobs WHERE job_type = 'embedding'"
        ).fetchone()[0]
        assert count == 1

    def test_skips_inactive_detections(self, db, data_root, detection):
        # Arrange
        db.execute(
            'UPDATE detections SET is_active = 0 WHERE id = :id',
            {'id': detection['detection_id']},
        )
        db.commit()

        # Act
        n = enqueue_pending(db)

        # Assert
        assert n == 0

    def test_species_filter_includes_matching(self, db, data_root, detection):
        # Act
        n = enqueue_pending(db, species=['felis catus'])

        # Assert
        assert n == 1

    def test_species_filter_excludes_non_matching(self, db, data_root, detection):
        # Act — filter for a different species
        n = enqueue_pending(db, species=['canis lupus'])

        # Assert
        assert n == 0

    def test_returns_count_of_new_jobs(self, db, data_root):
        # Arrange — two detections with crops
        for i in range(2):
            iid = _insert_image(db, data_root, name=f'IMG_00{i}.jpg')
            _insert_detection(db, data_root, iid, name=f'IMG_00{i}')

        # Act
        n = enqueue_pending(db)

        # Assert
        assert n == 2


# ---------------------------------------------------------------------------
# TestReidentifyAll
# ---------------------------------------------------------------------------

class TestReidentifyAll:
    """Test the reidentify_all function."""

    def _seed_algorithm_detection(self, db, data_root, individual_id, det_id):
        """Assign an individual to a detection as algorithm-assigned."""
        crop_rel = db.execute(
            'SELECT crop_path FROM detections WHERE id = :id', {'id': det_id},
        ).fetchone()['crop_path']
        emb_rel = _write_embedding(data_root, crop_rel, _unit([1, 0, 0, 0]))
        db.execute(
            '''
            UPDATE detections
            SET embedding_path = :ep, reid_model_name = 'mock',
                individual_id = :iid, individual_similarity = 0.9,
                individual_assigned_by = 'algorithm',
                individual_assigned_at = '2026-03-15T10:00:00+00:00'
            WHERE id = :did
            ''',
            {'ep': emb_rel, 'iid': individual_id, 'did': det_id},
        )
        db.commit()

    def test_clears_algorithm_assignment(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        self._seed_algorithm_detection(db, data_root, ind_id, detection['detection_id'])

        # Act
        reidentify_all(db)

        # Assert
        row = db.execute(
            'SELECT individual_id, embedding_path FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_id'] is None
        assert row['embedding_path'] is None

    def test_preserves_human_assignment(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        db.execute(
            "UPDATE detections SET individual_id = :iid, individual_assigned_by = 'human'"
            ' WHERE id = :did',
            {'iid': ind_id, 'did': detection['detection_id']},
        )
        db.commit()

        # Act
        reidentify_all(db)

        # Assert
        row = db.execute(
            'SELECT individual_id, individual_assigned_by FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_id'] == ind_id
        assert row['individual_assigned_by'] == 'human'

    def test_deletes_orphaned_individual(self, db, data_root, detection):
        # Arrange — individual with only an algorithm-assigned detection
        ind_id = _insert_individual(db)
        self._seed_algorithm_detection(db, data_root, ind_id, detection['detection_id'])

        # Act
        reidentify_all(db)

        # Assert
        row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': ind_id},
        ).fetchone()
        assert row is None

    def test_preserves_individual_with_human_detection(self, db, data_root, detection):
        # Arrange — individual anchored by a human-assigned detection
        ind_id = _insert_individual(db)
        db.execute(
            "UPDATE detections SET individual_id = :iid, individual_assigned_by = 'human'"
            ' WHERE id = :did',
            {'iid': ind_id, 'did': detection['detection_id']},
        )
        db.commit()

        # Act
        reidentify_all(db)

        # Assert
        row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': ind_id},
        ).fetchone()
        assert row is not None

    def test_resets_done_embedding_jobs_to_pending(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)
        db.execute(
            "UPDATE processing_jobs SET status = 'done' WHERE job_type = 'embedding'"
        )
        db.commit()

        # Act
        n = reidentify_all(db)

        # Assert
        assert n == 1
        status = db.execute(
            "SELECT status FROM processing_jobs WHERE job_type = 'embedding'"
        ).fetchone()['status']
        assert status == 'pending'

    def test_species_filter_only_clears_matching(self, db, data_root):
        # Arrange — one cat detection, one dog detection, each algorithm-assigned
        cat_label = 'a;b;c;d;e;f;g;felis catus'
        dog_label = 'a;b;c;d;e;f;g;canis lupus'
        cat_iid = _insert_individual(db, 'felis catus')
        dog_iid = _insert_individual(db, 'canis lupus')

        cat_img = _insert_image(db, data_root, 'cat.jpg')
        dog_img = _insert_image(db, data_root, 'dog.jpg')
        cat_det = _insert_detection(db, data_root, cat_img, label=cat_label, name='cat')
        dog_det = _insert_detection(db, data_root, dog_img, label=dog_label, name='dog')

        for det_id, ind_id in [(cat_det, cat_iid), (dog_det, dog_iid)]:
            crop_rel = db.execute(
                'SELECT crop_path FROM detections WHERE id = :id', {'id': det_id},
            ).fetchone()['crop_path']
            emb_rel = _write_embedding(data_root, crop_rel, _unit([1, 0, 0, 0]))
            db.execute(
                "UPDATE detections SET embedding_path = :ep, individual_id = :iid,"
                " individual_assigned_by = 'algorithm' WHERE id = :did",
                {'ep': emb_rel, 'iid': ind_id, 'did': det_id},
            )
        db.commit()

        # Act — reidentify only cats
        reidentify_all(db, species=['felis catus'])

        # Assert — cat detection cleared and cat individual row deleted; dog untouched
        cat_det_row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id', {'id': cat_det},
        ).fetchone()
        cat_ind_row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': cat_iid},
        ).fetchone()
        dog_det_row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id', {'id': dog_det},
        ).fetchone()
        dog_ind_row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': dog_iid},
        ).fetchone()
        assert cat_det_row['individual_id'] is None
        assert cat_ind_row is None
        assert dog_det_row['individual_id'] == dog_iid
        assert dog_ind_row is not None


# ---------------------------------------------------------------------------
# TestIdentifyPendingEmbedding
# ---------------------------------------------------------------------------

class TestIdentifyPendingEmbedding:
    """Test the embedding phase of identify_pending."""

    def test_writes_npy_file(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)
        identifier = _MockIdentifier()

        # Act
        identify_pending(data_root, db, identifier)

        # Assert
        emb_rel = db.execute(
            'SELECT embedding_path FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()['embedding_path']
        assert emb_rel is not None
        assert (data_root / emb_rel).exists()

    def test_embedding_path_ends_with_emb_npy(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)

        # Act
        identify_pending(data_root, db, _MockIdentifier())

        # Assert
        emb_rel = db.execute(
            'SELECT embedding_path FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()['embedding_path']
        assert emb_rel.endswith('_emb.npy')

    def test_stores_reid_model_provenance(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)

        # Act
        identify_pending(data_root, db, _MockIdentifier())

        # Assert
        row = db.execute(
            'SELECT reid_model_name, reid_model_version FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['reid_model_name'] == 'mock'
        assert row['reid_model_version'] == 'v0'

    def test_marks_job_done(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)

        # Act
        identify_pending(data_root, db, _MockIdentifier())

        # Assert
        job = db.execute(
            "SELECT status FROM processing_jobs WHERE detection_id = :id AND job_type = 'embedding'",
            {'id': detection['detection_id']},
        ).fetchone()
        assert job['status'] == 'done'

    def test_records_error_on_identifier_failure(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)

        # Act
        summary = identify_pending(data_root, db, _FailingIdentifier())

        # Assert
        assert 'IMG_001.jpg' in summary.errors
        job = db.execute(
            "SELECT status, error_msg FROM processing_jobs"
            " WHERE detection_id = :id AND job_type = 'embedding'",
            {'id': detection['detection_id']},
        ).fetchone()
        assert job['status'] == 'error'
        assert 'identifier exploded' in job['error_msg']

    def test_summary_embedded_count(self, db, data_root, detection):
        # Arrange
        enqueue_pending(db)

        # Act
        summary = identify_pending(data_root, db, _MockIdentifier())

        # Assert
        assert summary.embedded == 1

    def test_skips_done_jobs(self, db, data_root, detection):
        # Arrange — mark job as already done
        enqueue_pending(db)
        db.execute(
            "UPDATE processing_jobs SET status = 'done' WHERE job_type = 'embedding'"
        )
        db.commit()

        # Act
        summary = identify_pending(data_root, db, _MockIdentifier())

        # Assert
        assert summary.embedded == 0


# ---------------------------------------------------------------------------
# TestIdentifyPendingMatching
# ---------------------------------------------------------------------------

class TestIdentifyPendingMatching:
    """Test the gallery matching phase of identify_pending."""

    def _seed_embedded_detection(self, db, data_root, detection_id, vector):
        """Write an embedding file and update the detection row."""
        crop_rel = db.execute(
            'SELECT crop_path FROM detections WHERE id = :id', {'id': detection_id},
        ).fetchone()['crop_path']
        emb_rel = _write_embedding(data_root, crop_rel, vector)
        db.execute(
            "UPDATE detections SET embedding_path = :ep, reid_model_name = 'mock' WHERE id = :id",
            {'ep': emb_rel, 'id': detection_id},
        )
        db.commit()

    def test_creates_new_individual_for_first_detection(self, db, data_root, detection):
        # Arrange — embed the detection, no prior individuals
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        summary = identify_pending(data_root, db, _MockIdentifier())

        # Assert
        assert summary.identified == 1
        count = db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0]
        assert count == 1

    def test_founding_detection_gets_sentinel_similarity(self, db, data_root, detection):
        # Arrange
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        identify_pending(data_root, db, _MockIdentifier())

        # Assert
        row = db.execute(
            'SELECT individual_similarity FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_similarity'] == pytest.approx(1.0)

    def test_assigns_algorithm_as_source(self, db, data_root, detection):
        # Arrange
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        identify_pending(data_root, db, _MockIdentifier())

        # Assert
        row = db.execute(
            'SELECT individual_assigned_by FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_assigned_by'] == 'algorithm'

    def test_matches_existing_individual_above_threshold(self, db, data_root, detection):
        # Arrange — seed an existing individual with a similar embedding
        ind_id = _insert_individual(db)
        img2_id = _insert_image(db, data_root, 'IMG_002.jpg')
        det2_id = _insert_detection(db, data_root, img2_id, name='IMG_002')
        gallery_vec = _unit([1, 0, 0, 0])
        emb_rel = _write_embedding(data_root, f'derived/2026/03/15/IMG_002_det001.jpg', gallery_vec)
        db.execute(
            "UPDATE detections SET embedding_path = :ep, individual_id = :iid,"
            " individual_assigned_by = 'algorithm' WHERE id = :did",
            {'ep': emb_rel, 'iid': ind_id, 'did': det2_id},
        )
        db.commit()

        # seed the query detection with the same direction → similarity = 1.0
        query_vec = _unit([1, 0, 0, 0])
        self._seed_embedded_detection(db, data_root, detection['detection_id'], query_vec)

        # Act — threshold well below 1.0
        identify_pending(data_root, db, _MockIdentifier(), threshold=0.5)

        # Assert — matched to existing individual, not a new one
        row = db.execute(
            'SELECT individual_id, individual_similarity FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_id'] == ind_id
        assert row['individual_similarity'] == pytest.approx(1.0, abs=1e-5)
        assert db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0] == 1

    def test_creates_new_individual_below_threshold(self, db, data_root, detection):
        # Arrange — existing individual with orthogonal embedding (similarity = 0)
        ind_id = _insert_individual(db)
        img2_id = _insert_image(db, data_root, 'IMG_002.jpg')
        det2_id = _insert_detection(db, data_root, img2_id, name='IMG_002')
        emb_rel = _write_embedding(data_root, f'derived/2026/03/15/IMG_002_det001.jpg', _unit([1, 0, 0, 0]))
        db.execute(
            "UPDATE detections SET embedding_path = :ep, individual_id = :iid,"
            " individual_assigned_by = 'algorithm' WHERE id = :did",
            {'ep': emb_rel, 'iid': ind_id, 'did': det2_id},
        )
        db.commit()

        # query detection is orthogonal → similarity = 0
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([0, 1, 0, 0]))

        # Act — threshold above 0 → no match
        identify_pending(data_root, db, _MockIdentifier(), threshold=0.75)

        # Assert — new individual created
        assert db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0] == 2

    def test_in_memory_gallery_update_within_run(self, db, data_root):
        # Arrange — two detections of the same species, no prior gallery;
        # first should create a new individual, second should match it
        img1 = _insert_image(db, data_root, 'A.jpg')
        img2 = _insert_image(db, data_root, 'B.jpg')
        det1 = _insert_detection(db, data_root, img1, name='A')
        det2 = _insert_detection(db, data_root, img2, name='B')

        vec = _unit([1, 0, 0, 0])
        for det_id, name in [(det1, 'A'), (det2, 'B')]:
            self._seed_embedded_detection(db, data_root, det_id, vec)

        # Act — threshold low enough that the second matches the first
        identify_pending(data_root, db, _MockIdentifier(), threshold=0.5)

        # Assert — only one individual created; both detections share it
        assert db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0] == 1
        ids = [
            r['individual_id']
            for r in db.execute('SELECT individual_id FROM detections WHERE id IN (:a, :b)',
                                {'a': det1, 'b': det2}).fetchall()
        ]
        assert ids[0] == ids[1]


# ---------------------------------------------------------------------------
# TestResetAssignments
# ---------------------------------------------------------------------------

class TestResetAssignments:
    """Test the reset_assignments function."""

    def _seed_algorithm_detection(self, db, data_root, detection_id, individual_id):
        """Assign an individual to a detection as algorithm-assigned."""
        crop_rel = db.execute(
            'SELECT crop_path FROM detections WHERE id = :id', {'id': detection_id},
        ).fetchone()['crop_path']
        emb_rel = _write_embedding(data_root, crop_rel, _unit([1, 0, 0, 0]))
        db.execute(
            '''
            UPDATE detections
            SET embedding_path = :ep, reid_model_name = 'mock',
                individual_id = :iid, individual_similarity = 0.9,
                individual_assigned_by = 'algorithm',
                individual_assigned_at = '2026-03-15T10:00:00+00:00'
            WHERE id = :did
            ''',
            {'ep': emb_rel, 'iid': individual_id, 'did': detection_id},
        )
        db.commit()

    def test_clears_algorithm_assignment_fields(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        self._seed_algorithm_detection(db, data_root, detection['detection_id'], ind_id)

        # Act
        reset_assignments(db)

        # Assert
        row = db.execute(
            'SELECT individual_id, individual_similarity,'
            ' individual_assigned_by, individual_assigned_at'
            ' FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_id'] is None
        assert row['individual_similarity'] is None
        assert row['individual_assigned_by'] is None
        assert row['individual_assigned_at'] is None

    def test_preserves_embedding_fields(self, db, data_root, detection):
        # Arrange — embedding should survive reset_assignments
        ind_id = _insert_individual(db)
        self._seed_algorithm_detection(db, data_root, detection['detection_id'], ind_id)

        # Act
        reset_assignments(db)

        # Assert — embedding_path and reid_model_name still set
        row = db.execute(
            'SELECT embedding_path, reid_model_name FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['embedding_path'] is not None
        assert row['reid_model_name'] == 'mock'

    def test_preserves_human_assignment(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        db.execute(
            "UPDATE detections SET individual_id = :iid, individual_assigned_by = 'human'"
            ' WHERE id = :did',
            {'iid': ind_id, 'did': detection['detection_id']},
        )
        db.commit()

        # Act
        reset_assignments(db)

        # Assert — human detection untouched
        row = db.execute(
            'SELECT individual_id, individual_assigned_by FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_id'] == ind_id
        assert row['individual_assigned_by'] == 'human'

    def test_returns_count_of_cleared_detections(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        self._seed_algorithm_detection(db, data_root, detection['detection_id'], ind_id)

        # Act
        n = reset_assignments(db)

        # Assert
        assert n == 1

    def test_deletes_orphaned_individual(self, db, data_root, detection):
        # Arrange — individual with only algorithm-assigned detection
        ind_id = _insert_individual(db)
        self._seed_algorithm_detection(db, data_root, detection['detection_id'], ind_id)

        # Act
        reset_assignments(db)

        # Assert
        row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': ind_id},
        ).fetchone()
        assert row is None

    def test_preserves_individual_with_human_detection(self, db, data_root, detection):
        # Arrange — individual anchored by a human-assigned detection
        ind_id = _insert_individual(db)
        db.execute(
            "UPDATE detections SET individual_id = :iid, individual_assigned_by = 'human'"
            ' WHERE id = :did',
            {'iid': ind_id, 'did': detection['detection_id']},
        )
        db.commit()

        # Act
        reset_assignments(db)

        # Assert — individual survives
        row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': ind_id},
        ).fetchone()
        assert row is not None

    def test_species_filter_only_clears_matching(self, db, data_root):
        # Arrange — one cat and one dog, both algorithm-assigned
        cat_label = 'a;b;c;d;e;f;g;felis catus'
        dog_label = 'a;b;c;d;e;f;g;canis lupus'
        cat_iid = _insert_individual(db, 'felis catus')
        dog_iid = _insert_individual(db, 'canis lupus')

        cat_img = _insert_image(db, data_root, 'cat.jpg')
        dog_img = _insert_image(db, data_root, 'dog.jpg')
        cat_det = _insert_detection(db, data_root, cat_img, label=cat_label, name='cat')
        dog_det = _insert_detection(db, data_root, dog_img, label=dog_label, name='dog')

        for det_id, ind_id in [(cat_det, cat_iid), (dog_det, dog_iid)]:
            crop_rel = db.execute(
                'SELECT crop_path FROM detections WHERE id = :id', {'id': det_id},
            ).fetchone()['crop_path']
            emb_rel = _write_embedding(data_root, crop_rel, _unit([1, 0, 0, 0]))
            db.execute(
                "UPDATE detections SET embedding_path = :ep, individual_id = :iid,"
                " individual_assigned_by = 'algorithm' WHERE id = :did",
                {'ep': emb_rel, 'iid': ind_id, 'did': det_id},
            )
        db.commit()

        # Act — reset only cats
        reset_assignments(db, species=['felis catus'])

        # Assert — cat detection cleared and cat individual row deleted
        cat_det_row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id', {'id': cat_det},
        ).fetchone()
        cat_ind_row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': cat_iid},
        ).fetchone()
        dog_det_row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id', {'id': dog_det},
        ).fetchone()
        dog_ind_row = db.execute(
            'SELECT id FROM individuals WHERE id = :id', {'id': dog_iid},
        ).fetchone()
        assert cat_det_row['individual_id'] is None
        assert cat_ind_row is None
        assert dog_det_row['individual_id'] == dog_iid
        assert dog_ind_row is not None


# ---------------------------------------------------------------------------
# TestMatchPending
# ---------------------------------------------------------------------------

class TestMatchPending:
    """Test the match_pending function."""

    def _seed_embedded_detection(self, db, data_root, detection_id, vector):
        """Write an embedding file and update the detection row."""
        crop_rel = db.execute(
            'SELECT crop_path FROM detections WHERE id = :id', {'id': detection_id},
        ).fetchone()['crop_path']
        emb_rel = _write_embedding(data_root, crop_rel, vector)
        db.execute(
            "UPDATE detections SET embedding_path = :ep, reid_model_name = 'mock' WHERE id = :id",
            {'ep': emb_rel, 'id': detection_id},
        )
        db.commit()

    def test_returns_empty_summary_when_no_unmatched(self, db, data_root, detection):
        # Arrange — no embeddings set
        summary = match_pending(data_root, db)

        # Assert
        assert summary.identified == 0
        assert summary.embedded == 0

    def test_creates_new_individual_for_unmatched_detection(self, db, data_root, detection):
        # Arrange
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        summary = match_pending(data_root, db)

        # Assert
        assert summary.identified == 1
        count = db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0]
        assert count == 1

    def test_assigns_algorithm_as_source(self, db, data_root, detection):
        # Arrange
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        match_pending(data_root, db)

        # Assert
        row = db.execute(
            'SELECT individual_assigned_by FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_assigned_by'] == 'algorithm'

    def test_founding_detection_gets_sentinel_similarity(self, db, data_root, detection):
        # Arrange
        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        match_pending(data_root, db)

        # Assert
        row = db.execute(
            'SELECT individual_similarity FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_similarity'] == pytest.approx(1.0)

    def test_matches_existing_individual_above_threshold(self, db, data_root, detection):
        # Arrange — seed gallery with a similar embedding
        ind_id = _insert_individual(db)
        img2_id = _insert_image(db, data_root, 'IMG_002.jpg')
        det2_id = _insert_detection(db, data_root, img2_id, name='IMG_002')
        emb_rel = _write_embedding(
            data_root, 'derived/2026/03/15/IMG_002_det001.jpg', _unit([1, 0, 0, 0]),
        )
        db.execute(
            "UPDATE detections SET embedding_path = :ep, individual_id = :iid,"
            " individual_assigned_by = 'algorithm' WHERE id = :did",
            {'ep': emb_rel, 'iid': ind_id, 'did': det2_id},
        )
        db.commit()

        self._seed_embedded_detection(db, data_root, detection['detection_id'], _unit([1, 0, 0, 0]))

        # Act
        match_pending(data_root, db, threshold=0.5)

        # Assert — matched to existing, no new individual
        row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()
        assert row['individual_id'] == ind_id
        assert db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0] == 1

    def test_creates_new_individual_below_threshold(self, db, data_root, detection):
        # Arrange — existing individual with orthogonal embedding
        ind_id = _insert_individual(db)
        img2_id = _insert_image(db, data_root, 'IMG_002.jpg')
        det2_id = _insert_detection(db, data_root, img2_id, name='IMG_002')
        emb_rel = _write_embedding(
            data_root, 'derived/2026/03/15/IMG_002_det001.jpg', _unit([1, 0, 0, 0]),
        )
        db.execute(
            "UPDATE detections SET embedding_path = :ep, individual_id = :iid,"
            " individual_assigned_by = 'algorithm' WHERE id = :did",
            {'ep': emb_rel, 'iid': ind_id, 'did': det2_id},
        )
        db.commit()

        self._seed_embedded_detection(
            db, data_root, detection['detection_id'], _unit([0, 1, 0, 0]),
        )

        # Act — similarity = 0 < threshold
        match_pending(data_root, db, threshold=0.75)

        # Assert — new individual created
        assert db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0] == 2

    def test_in_memory_gallery_update_within_run(self, db, data_root):
        # Arrange — two identical detections, no prior gallery
        img1 = _insert_image(db, data_root, 'A.jpg')
        img2 = _insert_image(db, data_root, 'B.jpg')
        det1 = _insert_detection(db, data_root, img1, name='A')
        det2 = _insert_detection(db, data_root, img2, name='B')
        vec = _unit([1, 0, 0, 0])
        for det_id, name in [(det1, 'A'), (det2, 'B')]:
            crop_rel = db.execute(
                'SELECT crop_path FROM detections WHERE id = :id', {'id': det_id},
            ).fetchone()['crop_path']
            emb_rel = _write_embedding(data_root, crop_rel, vec)
            db.execute(
                "UPDATE detections SET embedding_path = :ep, reid_model_name = 'mock'"
                ' WHERE id = :id',
                {'ep': emb_rel, 'id': det_id},
            )
        db.commit()

        # Act — threshold low enough that second matches first
        match_pending(data_root, db, threshold=0.5)

        # Assert — only one individual; both share it
        assert db.execute('SELECT COUNT(*) FROM individuals').fetchone()[0] == 1
        ids = [
            r['individual_id']
            for r in db.execute(
                'SELECT individual_id FROM detections WHERE id IN (:a, :b)',
                {'a': det1, 'b': det2},
            ).fetchall()
        ]
        assert ids[0] == ids[1]

    def test_species_filter_restricts_matching(self, db, data_root):
        # Arrange — cat and dog, both unmatched and embedded
        cat_img = _insert_image(db, data_root, 'cat.jpg')
        dog_img = _insert_image(db, data_root, 'dog.jpg')
        cat_det = _insert_detection(
            db, data_root, cat_img,
            label='a;b;c;d;e;f;g;felis catus', name='cat',
        )
        dog_det = _insert_detection(
            db, data_root, dog_img,
            label='a;b;c;d;e;f;g;canis lupus', name='dog',
        )
        for det_id in [cat_det, dog_det]:
            crop_rel = db.execute(
                'SELECT crop_path FROM detections WHERE id = :id', {'id': det_id},
            ).fetchone()['crop_path']
            emb_rel = _write_embedding(data_root, crop_rel, _unit([1, 0, 0, 0]))
            db.execute(
                "UPDATE detections SET embedding_path = :ep, reid_model_name = 'mock'"
                ' WHERE id = :id',
                {'ep': emb_rel, 'id': det_id},
            )
        db.commit()

        # Act — match only cats
        summary = match_pending(data_root, db, species=['felis catus'])

        # Assert — only cat assigned, dog untouched
        assert summary.identified == 1
        cat_row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id', {'id': cat_det},
        ).fetchone()
        dog_row = db.execute(
            'SELECT individual_id FROM detections WHERE id = :id', {'id': dog_det},
        ).fetchone()
        assert cat_row['individual_id'] is not None
        assert dog_row['individual_id'] is None

    def test_skips_detection_with_missing_embedding_file(self, db, data_root, detection):
        # Arrange — set embedding_path to a nonexistent file
        db.execute(
            "UPDATE detections SET embedding_path = 'derived/missing_emb.npy'"
            ' WHERE id = :id',
            {'id': detection['detection_id']},
        )
        db.commit()

        # Act — should not raise, should just skip
        summary = match_pending(data_root, db)

        # Assert
        assert summary.identified == 0


# ---------------------------------------------------------------------------
# TestNextIndividualId
# ---------------------------------------------------------------------------

class TestNextIndividualId:
    """Test the _next_individual_id helper."""

    def test_returns_one_for_empty_table(self, db):
        assert _next_individual_id(db) == 1

    def test_returns_next_after_contiguous_sequence(self, db):
        # Arrange
        _insert_individual(db)  # id 1
        _insert_individual(db)  # id 2
        assert _next_individual_id(db) == 3

    def test_fills_gap_at_start(self, db):
        # Arrange — insert with explicit id 2, leaving 1 free
        db.execute(
            "INSERT INTO individuals (id, species_leaf, created_at, updated_at)"
            " VALUES (2, 'felis catus', 'now', 'now')"
        )
        db.commit()
        assert _next_individual_id(db) == 1

    def test_fills_interior_gap(self, db):
        # Arrange — ids 1 and 3 exist; 2 is missing
        db.execute(
            "INSERT INTO individuals (id, species_leaf, created_at, updated_at)"
            " VALUES (1, 'felis catus', 'now', 'now')"
        )
        db.execute(
            "INSERT INTO individuals (id, species_leaf, created_at, updated_at)"
            " VALUES (3, 'felis catus', 'now', 'now')"
        )
        db.commit()
        assert _next_individual_id(db) == 2

    def test_returns_one_after_all_rows_deleted(self, db):
        # Arrange — insert then delete; SQLite would normally pick max+1
        _insert_individual(db)
        _insert_individual(db)
        db.execute('DELETE FROM individuals')
        db.commit()
        assert _next_individual_id(db) == 1


# ---------------------------------------------------------------------------
# TestBuildSpeciesFilter
# ---------------------------------------------------------------------------

class TestBuildSpeciesFilter:
    """Test the _build_species_filter helper."""

    def test_returns_empty_clause_for_none(self):
        result = _build_species_filter(None)
        assert result['clause'] == ''
        assert result['params'] == {}

    def test_returns_empty_clause_for_empty_list(self):
        result = _build_species_filter([])
        assert result['clause'] == ''
        assert result['params'] == {}

    def test_single_species_clause(self):
        result = _build_species_filter(['felis catus'])
        assert 'd.label LIKE :labellike0' in result['clause']
        assert result['params']['labellike0'] == '%;felis catus'

    def test_multiple_species_joined_with_or(self):
        result = _build_species_filter(['felis catus', 'canis lupus'])
        assert 'OR' in result['clause']
        assert result['params']['labellike0'] == '%;felis catus'
        assert result['params']['labellike1'] == '%;canis lupus'

    def test_empty_table_alias_omits_prefix(self):
        result = _build_species_filter(['felis catus'], table_alias='')
        assert 'label LIKE :labellike0' in result['clause']
        assert 'd.label' not in result['clause']


# ---------------------------------------------------------------------------
# TestGetGallery
# ---------------------------------------------------------------------------

class TestGetGallery:
    """Test the _get_gallery helper."""

    def test_returns_empty_for_no_assigned_detections(self, db, data_root, detection):
        result = _get_gallery(db, data_root, 'felis catus')
        assert result == []

    def test_returns_entry_for_assigned_detection_with_embedding(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        vec = _unit([1, 0, 0, 0])
        crop_rel = db.execute(
            'SELECT crop_path FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()['crop_path']
        emb_rel = _write_embedding(data_root, crop_rel, vec)
        db.execute(
            "UPDATE detections SET embedding_path = :ep, individual_id = :iid"
            " WHERE id = :did",
            {'ep': emb_rel, 'iid': ind_id, 'did': detection['detection_id']},
        )
        db.commit()

        # Act
        gallery = _get_gallery(db, data_root, 'felis catus')

        # Assert
        assert len(gallery) == 1
        assert gallery[0][0] == ind_id
        np.testing.assert_allclose(gallery[0][1], vec, atol=1e-6)

    def test_excludes_inactive_detections(self, db, data_root, detection):
        # Arrange
        ind_id = _insert_individual(db)
        crop_rel = db.execute(
            'SELECT crop_path FROM detections WHERE id = :id',
            {'id': detection['detection_id']},
        ).fetchone()['crop_path']
        emb_rel = _write_embedding(data_root, crop_rel, _unit([1, 0, 0, 0]))
        db.execute(
            'UPDATE detections SET is_active = 0, embedding_path = :ep,'
            ' individual_id = :iid WHERE id = :did',
            {'ep': emb_rel, 'iid': ind_id, 'did': detection['detection_id']},
        )
        db.commit()

        # Act
        gallery = _get_gallery(db, data_root, 'felis catus')

        # Assert
        assert gallery == []


# ---------------------------------------------------------------------------
# TestMergeIndividuals
# ---------------------------------------------------------------------------

class TestMergeIndividuals:
    """Test the merge_individuals function."""

    def _seed_detection_with_individual(self, db, data_root, individual_id, name, assigned_by='algorithm'):
        """Insert an image+detection and assign it to the given individual."""
        image_id = _insert_image(db, data_root, f'{name}.jpg')
        det_id = _insert_detection(db, data_root, image_id, name=name)
        db.execute(
            f"UPDATE detections SET individual_id = :iid, individual_assigned_by = :by,"
            f" individual_assigned_at = 'now', individual_similarity = 0.9"
            f' WHERE id = :did',
            {'iid': individual_id, 'by': assigned_by, 'did': det_id},
        )
        db.commit()
        return det_id

    def test_returns_target_id(self, db, data_root):
        # Arrange
        ind1 = _insert_individual(db)
        ind2 = _insert_individual(db)
        ind3 = _insert_individual(db)

        # Act
        target = merge_individuals(db, [ind1, ind2, ind3])

        # Assert
        assert target == ind1

    def test_target_is_lowest_id(self, db, data_root):
        # Arrange — insert in non-sequential order
        ind5 = db.execute(
            "INSERT INTO individuals (id, species_leaf, created_at, updated_at)"
            " VALUES (5, 'felis catus', 'now', 'now')"
        ) and db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.execute(
            "INSERT INTO individuals (id, species_leaf, created_at, updated_at)"
            " VALUES (2, 'felis catus', 'now', 'now')"
        )
        db.execute(
            "INSERT INTO individuals (id, species_leaf, created_at, updated_at)"
            " VALUES (8, 'felis catus', 'now', 'now')"
        )
        db.commit()

        target = merge_individuals(db, [5, 2, 8])
        assert target == 2

    def test_reassigns_detections_to_target(self, db, data_root):
        # Arrange
        ind1 = _insert_individual(db)
        ind2 = _insert_individual(db)
        det1 = self._seed_detection_with_individual(db, data_root, ind1, 'A')
        det2 = self._seed_detection_with_individual(db, data_root, ind2, 'B')

        # Act
        merge_individuals(db, [ind1, ind2])

        # Assert — both detections point to ind1
        for det_id in [det1, det2]:
            row = db.execute(
                'SELECT individual_id FROM detections WHERE id = :id', {'id': det_id},
            ).fetchone()
            assert row['individual_id'] == ind1

    def test_merged_detections_marked_human(self, db, data_root):
        # Arrange
        ind1 = _insert_individual(db)
        ind2 = _insert_individual(db)
        det1 = self._seed_detection_with_individual(db, data_root, ind1, 'A')
        det2 = self._seed_detection_with_individual(db, data_root, ind2, 'B')

        # Act
        merge_individuals(db, [ind1, ind2])

        # Assert — both detections are now human-assigned
        for det_id in [det1, det2]:
            row = db.execute(
                'SELECT individual_assigned_by FROM detections WHERE id = :id',
                {'id': det_id},
            ).fetchone()
            assert row['individual_assigned_by'] == 'human'

    def test_individual_similarity_cleared(self, db, data_root):
        # Arrange
        ind1 = _insert_individual(db)
        ind2 = _insert_individual(db)
        det = self._seed_detection_with_individual(db, data_root, ind2, 'A')

        # Act
        merge_individuals(db, [ind1, ind2])

        # Assert
        row = db.execute(
            'SELECT individual_similarity FROM detections WHERE id = :id', {'id': det},
        ).fetchone()
        assert row['individual_similarity'] is None

    def test_non_target_individuals_deleted(self, db, data_root):
        # Arrange
        ind1 = _insert_individual(db)
        ind2 = _insert_individual(db)
        ind3 = _insert_individual(db)

        # Act
        merge_individuals(db, [ind1, ind2, ind3])

        # Assert — ind2 and ind3 gone; ind1 survives
        assert db.execute('SELECT id FROM individuals WHERE id = :id', {'id': ind1}).fetchone() is not None
        assert db.execute('SELECT id FROM individuals WHERE id = :id', {'id': ind2}).fetchone() is None
        assert db.execute('SELECT id FROM individuals WHERE id = :id', {'id': ind3}).fetchone() is None

    def test_raises_for_fewer_than_two_ids(self, db):
        ind1 = _insert_individual(db)
        with pytest.raises(ValueError, match='at least two'):
            merge_individuals(db, [ind1])

    def test_raises_for_missing_id(self, db):
        ind1 = _insert_individual(db)
        with pytest.raises(ValueError, match='not found'):
            merge_individuals(db, [ind1, 9999])
