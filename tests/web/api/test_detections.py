"""Tests for the detections API endpoints.

Focused on cases that caused real regressions:
- list_detections and recent_by_species crash when any detection has confidence=NULL
- patch_detection must update both label and confidence (null for human annotations)
"""



# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _insert_media(db, media_id: int = 1, captured_at: str = '2026-01-01T00:00:00') -> None:
    db.execute(
        '''
        INSERT INTO media (id, path, filename, ingested_at, file_hash, file_size, captured_at)
        VALUES (:id, :path, :filename, :ingested_at, :file_hash, :file_size, :captured_at)
        ''',
        {
            'id': media_id,
            'path': f'media/2026/01/01/img{media_id:04d}.jpg',
            'filename': f'img{media_id:04d}.jpg',
            'ingested_at': '2026-01-01T00:00:00',
            'file_hash': f'hash{media_id:04d}',
            'file_size': 1024,
            'captured_at': captured_at,
        },
    )
    db.commit()


def _insert_detection(
    db,
    det_id: int,
    media_id: int = 1,
    label: str = 'abc;animalia;chordata;mammalia;carnivora;canidae;vulpes;vulpes vulpes',
    confidence: float | None = 0.91,
    crop_path: str = 'derived/2026/01/01/det0001.jpg',
    individual_id: int | None = None,
    label_assigned_by: str = 'algorithm',
) -> None:
    db.execute(
        '''
        INSERT INTO detections (id, media_id, label, confidence, crop_path,
                                individual_id, label_assigned_by, created_at, is_active)
        VALUES (:id, :media_id, :label, :confidence, :crop_path,
                :individual_id, :label_assigned_by, :created_at, 1)
        ''',
        {
            'id': det_id,
            'media_id': media_id,
            'label': label,
            'confidence': confidence,
            'crop_path': crop_path,
            'individual_id': individual_id,
            'label_assigned_by': label_assigned_by,
            'created_at': '2026-01-01T00:00:00',
        },
    )
    db.commit()


def _insert_individual(db, ind_id: int, species_leaf: str = 'vulpes vulpes', nickname: str | None = None) -> None:
    db.execute(
        '''
        INSERT INTO individuals (id, species_leaf, nickname, created_at, updated_at)
        VALUES (:id, :species_leaf, :nickname, :created_at, :updated_at)
        ''',
        {
            'id': ind_id,
            'species_leaf': species_leaf,
            'nickname': nickname,
            'created_at': '2026-01-01T00:00:00',
            'updated_at': '2026-01-01T00:00:00',
        },
    )
    db.commit()


# ---------------------------------------------------------------------------
# GET /api/detections
# ---------------------------------------------------------------------------

class TestListDetections:
    """Test the list_detections endpoint."""

    def test_list_detections_returns_detections(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=0.85)

        response = client.get('/api/detections')

        assert response.status_code == 200
        body = response.json()
        assert body['total'] == 1
        assert len(body['detections']) == 1
        assert body['detections'][0]['confidence'] == 0.85

    def test_list_detections_null_confidence_does_not_crash(self, client, db):
        """Regression: round(None, 3) raises TypeError — confidence must be guarded."""
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=None, label_assigned_by='human')

        response = client.get('/api/detections')

        assert response.status_code == 200
        det = response.json()['detections'][0]
        assert det['confidence'] is None

    def test_list_detections_mixed_confidence(self, client, db):
        """Both null and non-null confidence rows are returned correctly."""
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=0.90)
        _insert_detection(
            db, det_id=2, confidence=None, label_assigned_by='human',
            crop_path='derived/2026/01/01/det0002.jpg',
        )

        response = client.get('/api/detections')

        assert response.status_code == 200
        body = response.json()
        assert body['total'] == 2
        by_id = {d['id']: d for d in body['detections']}
        assert by_id[1]['confidence'] == 0.90
        assert by_id[2]['confidence'] is None

    def test_list_detections_leaf_label_returned(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        response = client.get('/api/detections')

        assert response.json()['detections'][0]['label'] == 'vulpes vulpes'

    def test_list_detections_excludes_blank(self, client, db):
        _insert_media(db)
        _insert_detection(
            db, det_id=1,
            label='abc;;;;;blank',
            crop_path='derived/2026/01/01/blank0001.jpg',
        )

        response = client.get('/api/detections')

        assert response.json()['total'] == 0

    def test_list_detections_species_filter(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(
            db, det_id=2,
            label='xyz;animalia;chordata;mammalia;carnivora;felidae;felis;domestic cat',
            crop_path='derived/2026/01/01/det0002.jpg',
        )

        response = client.get('/api/detections?species=domestic+cat')

        assert response.status_code == 200
        body = response.json()
        assert body['total'] == 1
        assert body['detections'][0]['label'] == 'domestic cat'


# ---------------------------------------------------------------------------
# GET /api/detections/recent_by_species
# ---------------------------------------------------------------------------

class TestRecentBySpecies:
    """Test the recent_by_species endpoint."""

    def test_recent_by_species_returns_one_per_species(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(
            db, det_id=2,
            crop_path='derived/2026/01/01/det0002.jpg',
        )

        response = client.get('/api/detections/recent_by_species')

        assert response.status_code == 200
        data = response.json()
        # same species — only the most recent (highest id) should appear
        assert len(data) == 1
        assert data[0]['id'] == 2

    def test_recent_by_species_null_confidence_does_not_crash(self, client, db):
        """Regression: null confidence must not raise TypeError in recent_by_species."""
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=None, label_assigned_by='human')

        response = client.get('/api/detections/recent_by_species')

        assert response.status_code == 200
        assert response.json()[0]['confidence'] is None

    def test_recent_by_species_leaf_label_returned(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        response = client.get('/api/detections/recent_by_species')

        assert response.json()[0]['label'] == 'vulpes vulpes'


# ---------------------------------------------------------------------------
# PATCH /api/detections/{detection_id}
# ---------------------------------------------------------------------------

class TestPatchDetection:
    """Test the patch_detection endpoint."""

    def test_patch_sets_human_label_and_clears_confidence(self, client, db):
        """Regression: after a human save, confidence must be null in the response."""
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=0.88)

        response = client.patch(
            '/api/detections/1',
            json={'species_leaf': 'vulpes vulpes', 'individual_id': None},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['confidence'] is None
        assert body['label_assigned_by'] == 'human'

    def test_patch_unknown_species_returns_422(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        response = client.patch(
            '/api/detections/1',
            json={'species_leaf': 'not a real species', 'individual_id': None},
        )

        assert response.status_code == 422

    def test_patch_missing_detection_returns_404(self, client, db):
        response = client.patch(
            '/api/detections/999',
            json={'species_leaf': 'vulpes vulpes', 'individual_id': None},
        )

        assert response.status_code == 404

    def test_patch_response_label_is_full_taxonomy(self, client, db):
        """get_detection (called by patch) returns the full taxonomy string, not just the leaf."""
        _insert_media(db)
        _insert_detection(db, det_id=1)

        response = client.patch(
            '/api/detections/1',
            json={'species_leaf': 'vulpes vulpes', 'individual_id': None},
        )

        full_label = response.json()['label']
        assert ';' in full_label
        assert full_label.endswith('vulpes vulpes')



# ---------------------------------------------------------------------------
# DELETE /api/media/{media_id}
# ---------------------------------------------------------------------------

class TestDeleteMedia:
    """Test the delete_media endpoint."""

    def test_delete_removes_media_and_detections(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        response = client.delete('/api/media/1')

        assert response.status_code == 200
        assert response.json() == {'deleted': 1}
        assert db.execute('SELECT COUNT(*) FROM media').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM detections').fetchone()[0] == 0

    def test_delete_missing_media_returns_404(self, client, db):
        response = client.delete('/api/media/999')
        assert response.status_code == 404

    def test_delete_orphans_individual_when_last_detection_removed(self, client, db):
        """Deleting the only media linked to an individual must remove that individual."""
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1)

        client.delete('/api/media/1')

        assert db.execute('SELECT COUNT(*) FROM individuals WHERE id = 1').fetchone()[0] == 0

    def test_delete_preserves_individual_when_other_detections_remain(self, client, db):
        """Individual must survive if it still has detections on other media."""
        _insert_media(db, media_id=1)
        _insert_media(db, media_id=2)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, media_id=1, individual_id=1)
        _insert_detection(db, det_id=2, media_id=2, individual_id=1,
                          crop_path='derived/2026/01/01/det0002.jpg')

        client.delete('/api/media/1')

        assert db.execute('SELECT COUNT(*) FROM individuals WHERE id = 1').fetchone()[0] == 1

    def test_delete_removes_only_orphaned_individuals(self, client, db):
        """Only the individual whose last detection was removed is deleted."""
        _insert_media(db, media_id=1)
        _insert_media(db, media_id=2)
        _insert_individual(db, ind_id=1)
        _insert_individual(db, ind_id=2)
        # individual 1 has one detection on media 1 (being deleted)
        _insert_detection(db, det_id=1, media_id=1, individual_id=1)
        # individual 2 has detections on both media items
        _insert_detection(db, det_id=2, media_id=1, individual_id=2,
                          crop_path='derived/2026/01/01/det0002.jpg')
        _insert_detection(db, det_id=3, media_id=2, individual_id=2,
                          crop_path='derived/2026/01/01/det0003.jpg')

        client.delete('/api/media/1')

        assert db.execute('SELECT COUNT(*) FROM individuals WHERE id = 1').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM individuals WHERE id = 2').fetchone()[0] == 1


class TestPatchDetectionFilterBehavior:
    """Tests for filter-aware behavior after patching a detection."""

    def test_patch_removes_detection_from_previous_species_filter(self, client, db):
        """After patching species, the detection must not appear under the old species filter.

        This is the scenario that motivated refreshing the grid after a single-detection
        save: if filtered to 'vulpes vulpes' and the user relabels a detection as
        'domestic cat', that card should disappear from the filtered view on save.
        """
        cat_label = 'xyz;animalia;chordata;mammalia;carnivora;felidae;felis;domestic cat'
        fox_label = 'abc;animalia;chordata;mammalia;carnivora;canidae;vulpes;vulpes vulpes'
        _insert_media(db)
        _insert_detection(db, det_id=1, label=fox_label)
        # a second fox detection gives the PATCH endpoint a label to resolve 'domestic cat' from
        _insert_detection(db, det_id=2, label=cat_label, crop_path='derived/2026/01/01/det0002.jpg')

        client.patch('/api/detections/1', json={'species_leaf': 'domestic cat', 'individual_id': None})

        fox_response = client.get('/api/detections?species=vulpes+vulpes')
        cat_response = client.get('/api/detections?species=domestic+cat')
        assert fox_response.json()['total'] == 0
        assert cat_response.json()['total'] == 2
