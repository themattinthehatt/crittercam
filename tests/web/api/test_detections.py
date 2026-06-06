"""Tests for the detections API endpoints.

Focused on cases that caused real regressions:
- list_detections and recent_by_species crash when any detection has confidence=NULL
- patch_detection must update both label and confidence (null for human annotations)
"""



# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _insert_deployment(db, dep_id: int = 1, deployment_name: str | None = 'test deployment') -> None:
    db.execute(
        'INSERT INTO deployments (id, deployment_name) VALUES (:id, :name)',
        {'id': dep_id, 'name': deployment_name},
    )
    db.commit()


def _insert_media(
    db,
    media_id: int = 1,
    captured_at: str = '2026-01-01T00:00:00',
    deployment_id: int | None = None,
) -> None:
    db.execute(
        '''
        INSERT INTO media (id, deployment_id, path, filename, ingested_at, file_hash, file_size, captured_at)
        VALUES (:id, :deployment_id, :path, :filename, :ingested_at, :file_hash, :file_size, :captured_at)
        ''',
        {
            'id': media_id,
            'deployment_id': deployment_id,
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


# ---------------------------------------------------------------------------
# GET /api/deployments
# ---------------------------------------------------------------------------

class TestListDeployments:
    """Test the list_deployments endpoint."""

    def test_list_deployments_returns_deployment_with_media(self, client, db):
        _insert_deployment(db)
        _insert_media(db, deployment_id=1)

        response = client.get('/api/deployments')

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['id'] == 1
        assert data[0]['deployment_name'] == 'test deployment'

    def test_list_deployments_excludes_deployment_without_media(self, client, db):
        _insert_deployment(db, dep_id=1)
        _insert_deployment(db, dep_id=2, deployment_name='empty deployment')
        _insert_media(db, deployment_id=1)

        response = client.get('/api/deployments')

        data = response.json()
        assert len(data) == 1
        assert data[0]['id'] == 1

    def test_list_deployments_empty_when_no_deployments(self, client, db):
        response = client.get('/api/deployments')

        assert response.status_code == 200
        assert response.json() == []

    def test_list_deployments_null_name_returned(self, client, db):
        _insert_deployment(db, dep_id=1, deployment_name=None)
        _insert_media(db, deployment_id=1)

        response = client.get('/api/deployments')

        assert response.json()[0]['deployment_name'] is None

    def test_list_deployments_ordered_by_id(self, client, db):
        _insert_deployment(db, dep_id=2, deployment_name='second')
        _insert_deployment(db, dep_id=1, deployment_name='first')
        _insert_media(db, media_id=1, deployment_id=1)
        _insert_media(db, media_id=2, deployment_id=2)

        response = client.get('/api/deployments')

        assert [d['id'] for d in response.json()] == [1, 2]


# ---------------------------------------------------------------------------
# GET /api/detections — deployment_id filter
# ---------------------------------------------------------------------------

class TestListDetectionsDeploymentFilter:
    """Test deployment_id filtering on list_detections."""

    def test_deployment_filter_returns_matching_detections(self, client, db):
        _insert_deployment(db, dep_id=1)
        _insert_deployment(db, dep_id=2)
        _insert_media(db, media_id=1, deployment_id=1)
        _insert_media(db, media_id=2, deployment_id=2)
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        response = client.get('/api/detections?deployment_id=1')

        assert response.status_code == 200
        body = response.json()
        assert body['total'] == 1
        assert body['detections'][0]['id'] == 1

    def test_deployment_filter_excludes_other_deployments(self, client, db):
        _insert_deployment(db, dep_id=1)
        _insert_deployment(db, dep_id=2)
        _insert_media(db, media_id=1, deployment_id=1)
        _insert_media(db, media_id=2, deployment_id=2)
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        response = client.get('/api/detections?deployment_id=2')

        body = response.json()
        assert body['total'] == 1
        assert body['detections'][0]['id'] == 2

    def test_deployment_filter_no_results_when_no_match(self, client, db):
        _insert_deployment(db, dep_id=1)
        _insert_deployment(db, dep_id=2)
        _insert_media(db, media_id=1, deployment_id=1)
        _insert_detection(db, det_id=1, media_id=1)

        response = client.get('/api/detections?deployment_id=2')

        assert response.json()['total'] == 0

    def test_deployment_filter_combined_with_species(self, client, db):
        """deployment_id and species can be combined — only the intersection is returned."""
        fox = 'abc;animalia;chordata;mammalia;carnivora;canidae;vulpes;vulpes vulpes'
        cat = 'xyz;animalia;chordata;mammalia;carnivora;felidae;felis;domestic cat'
        _insert_deployment(db, dep_id=1)
        _insert_media(db, media_id=1, deployment_id=1)
        _insert_detection(db, det_id=1, media_id=1, label=fox)
        _insert_detection(db, det_id=2, media_id=1, label=cat, crop_path='derived/2026/01/01/det0002.jpg')

        response = client.get('/api/detections?deployment_id=1&species=vulpes+vulpes')

        body = response.json()
        assert body['total'] == 1
        assert body['detections'][0]['label'] == 'vulpes vulpes'

    def test_deployment_filter_combined_with_only_favorites(self, client, db):
        """deployment_id and only_favorites can be combined."""
        _insert_deployment(db, dep_id=1)
        _insert_media(db, media_id=1, deployment_id=1)
        _insert_media(db, media_id=2, deployment_id=1)
        db.execute('UPDATE media SET favorite = 1 WHERE id = 1')
        db.commit()
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        response = client.get('/api/detections?deployment_id=1&only_favorites=true')

        body = response.json()
        assert body['total'] == 1
        assert body['detections'][0]['id'] == 1


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


# ---------------------------------------------------------------------------
# GET /api/detections — individual_id, date_from, date_to, only_favorites
# ---------------------------------------------------------------------------

class TestListDetectionsFilters:
    """Test individual_id, date_from, date_to, and only_favorites filters on list_detections."""

    def test_individual_id_filter_returns_only_matching_detections(self, client, db):
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1)
        _insert_detection(db, det_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        body = client.get('/api/detections?individual_id=1').json()

        assert body['total'] == 1
        assert body['detections'][0]['individual_id'] == 1

    def test_individual_id_filter_returns_empty_when_no_match(self, client, db):
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_individual(db, ind_id=2)
        _insert_detection(db, det_id=1, individual_id=1)

        body = client.get('/api/detections?individual_id=2').json()

        assert body['total'] == 0

    def test_date_from_excludes_older_detections(self, client, db):
        _insert_media(db, media_id=1, captured_at='2025-01-01T10:00:00')
        _insert_media(db, media_id=2, captured_at='2026-01-01T10:00:00')
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        body = client.get('/api/detections?date_from=2026-01-01').json()

        assert body['total'] == 1
        assert body['detections'][0]['id'] == 2

    def test_date_to_excludes_newer_detections(self, client, db):
        _insert_media(db, media_id=1, captured_at='2025-01-01T10:00:00')
        _insert_media(db, media_id=2, captured_at='2026-06-01T10:00:00')
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        body = client.get('/api/detections?date_to=2025-12-31').json()

        assert body['total'] == 1
        assert body['detections'][0]['id'] == 1

    def test_date_to_includes_detections_on_the_cutoff_day(self, client, db):
        """date_to is inclusive — detections captured on that exact day must appear."""
        _insert_media(db, captured_at='2025-06-01T23:59:59')
        _insert_detection(db, det_id=1)

        body = client.get('/api/detections?date_to=2025-06-01').json()

        assert body['total'] == 1

    def test_date_range_combined(self, client, db):
        _insert_media(db, media_id=1, captured_at='2024-01-15T10:00:00')
        _insert_media(db, media_id=2, captured_at='2025-06-15T10:00:00')
        _insert_media(db, media_id=3, captured_at='2026-01-15T10:00:00')
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')
        _insert_detection(db, det_id=3, media_id=3, crop_path='derived/2026/01/01/det0003.jpg')

        body = client.get('/api/detections?date_from=2025-01-01&date_to=2025-12-31').json()

        assert body['total'] == 1
        assert body['detections'][0]['id'] == 2

    def test_only_favorites_excludes_non_favorited_media(self, client, db):
        _insert_media(db, media_id=1)
        _insert_media(db, media_id=2)
        db.execute('UPDATE media SET favorite = 1 WHERE id = 1')
        db.commit()
        _insert_detection(db, det_id=1, media_id=1)
        _insert_detection(db, det_id=2, media_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        body = client.get('/api/detections?only_favorites=true').json()

        assert body['total'] == 1
        assert body['detections'][0]['id'] == 1

    def test_only_favorites_returns_empty_when_none_favorited(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        body = client.get('/api/detections?only_favorites=true').json()

        assert body['total'] == 0


# ---------------------------------------------------------------------------
# GET /api/detections — pagination
# ---------------------------------------------------------------------------

class TestListDetectionsPagination:
    """Test page and page_size parameters on list_detections."""

    @staticmethod
    def _seed(db: object, n: int) -> None:
        """Insert one media row and n detections for pagination tests."""
        _insert_media(db)
        for i in range(1, n + 1):
            _insert_detection(db, det_id=i, crop_path=f'derived/2026/01/01/det{i:04d}.jpg')

    def test_default_page_size_is_24(self, client, db):
        self._seed(db, 30)

        body = client.get('/api/detections').json()

        assert body['page_size'] == 24
        assert len(body['detections']) == 24
        assert body['total'] == 30

    def test_page_2_returns_remaining_items(self, client, db):
        self._seed(db, 30)

        body = client.get('/api/detections?page=2').json()

        assert len(body['detections']) == 6
        assert body['page'] == 2

    def test_custom_page_size(self, client, db):
        self._seed(db, 10)

        body = client.get('/api/detections?page_size=3').json()

        assert len(body['detections']) == 3
        assert body['page_size'] == 3
        assert body['total'] == 10

    def test_total_independent_of_page(self, client, db):
        """total always reflects the full count, not just items on the current page."""
        self._seed(db, 30)

        body1 = client.get('/api/detections?page=1').json()
        body2 = client.get('/api/detections?page=2').json()

        assert body1['total'] == body2['total'] == 30


# ---------------------------------------------------------------------------
# GET /api/species
# ---------------------------------------------------------------------------

class TestListSpecies:
    """Test the list_species endpoint."""

    def test_returns_empty_for_empty_db(self, client, db):
        response = client.get('/api/species')

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_leaf_label(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        response = client.get('/api/species')

        assert response.json() == ['vulpes vulpes']

    def test_excludes_blank_labels(self, client, db):
        _insert_media(db)
        _insert_detection(
            db, det_id=1, label='abc;;;;;blank', crop_path='derived/2026/01/01/blank0001.jpg',
        )

        response = client.get('/api/species')

        assert response.json() == []

    def test_excludes_detections_without_crop(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1, crop_path=None)

        response = client.get('/api/species')

        assert response.json() == []

    def test_deduplicates_same_species(self, client, db):
        """Multiple detections of the same species appear as a single entry."""
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(db, det_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        response = client.get('/api/species')

        assert response.json().count('vulpes vulpes') == 1

    def test_returns_sorted_alphabetically(self, client, db):
        cat_label = 'xyz;animalia;chordata;mammalia;carnivora;felidae;felis;domestic cat'
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(db, det_id=2, label=cat_label, crop_path='derived/2026/01/01/det0002.jpg')

        species = client.get('/api/species').json()

        assert species == sorted(species)
        assert 'vulpes vulpes' in species
        assert 'domestic cat' in species


# ---------------------------------------------------------------------------
# GET /api/individuals
# ---------------------------------------------------------------------------

class TestListIndividuals:
    """Test the list_individuals endpoint."""

    def test_returns_empty_for_empty_db(self, client, db):
        response = client.get('/api/individuals')

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_individual_with_active_detection_and_crop(self, client, db):
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1)

        data = client.get('/api/individuals').json()

        assert len(data) == 1
        assert data[0]['id'] == 1
        assert data[0]['species_leaf'] == 'vulpes vulpes'

    def test_excludes_individual_with_no_detections(self, client, db):
        _insert_individual(db, ind_id=1)

        data = client.get('/api/individuals').json()

        assert data == []

    def test_excludes_individual_with_inactive_detection(self, client, db):
        """Individual linked only to is_active=0 detections must not appear."""
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1)
        db.execute('UPDATE detections SET is_active = 0 WHERE id = 1')
        db.commit()

        data = client.get('/api/individuals').json()

        assert data == []

    def test_excludes_individual_with_no_crop(self, client, db):
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1, crop_path=None)

        data = client.get('/api/individuals').json()

        assert data == []

    def test_nickname_returned(self, client, db):
        _insert_media(db)
        _insert_individual(db, ind_id=1, nickname='Rusty')
        _insert_detection(db, det_id=1, individual_id=1)

        data = client.get('/api/individuals').json()

        assert data[0]['nickname'] == 'Rusty'

    def test_nickname_is_null_when_not_set(self, client, db):
        _insert_media(db)
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1)

        data = client.get('/api/individuals').json()

        assert data[0]['nickname'] is None

    def test_ordered_by_id(self, client, db):
        cat_label = 'xyz;animalia;chordata;mammalia;carnivora;felidae;felis;domestic cat'
        _insert_media(db)
        _insert_individual(db, ind_id=2, species_leaf='domestic cat')
        _insert_individual(db, ind_id=1)
        _insert_detection(db, det_id=1, individual_id=1)
        _insert_detection(
            db, det_id=2, individual_id=2, label=cat_label,
            crop_path='derived/2026/01/01/det0002.jpg',
        )

        data = client.get('/api/individuals').json()

        assert [d['id'] for d in data] == [1, 2]


# ---------------------------------------------------------------------------
# GET /api/detections/{detection_id}
# ---------------------------------------------------------------------------

class TestGetDetection:
    """Test the GET /api/detections/{detection_id} endpoint."""

    def test_returns_detection_by_id(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=0.95)

        response = client.get('/api/detections/1')

        assert response.status_code == 200
        body = response.json()
        assert body['id'] == 1
        assert body['confidence'] == 0.95

    def test_returns_404_for_missing_detection(self, client, db):
        response = client.get('/api/detections/999')

        assert response.status_code == 404

    def test_returns_full_taxonomy_label(self, client, db):
        """get_detection returns the full ';'-joined taxonomy string, not just the leaf."""
        _insert_media(db)
        _insert_detection(db, det_id=1)

        body = client.get('/api/detections/1').json()

        assert ';' in body['label']
        assert body['label'].endswith('vulpes vulpes')

    def test_prev_id_and_next_id_null_at_boundaries(self, client, db):
        """Only detection in the db — both neighbours are null."""
        _insert_media(db)
        _insert_detection(db, det_id=1)

        body = client.get('/api/detections/1').json()

        assert body['prev_id'] is None
        assert body['next_id'] is None

    def test_prev_id_set_when_lower_detection_exists(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(db, det_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        body = client.get('/api/detections/2').json()

        assert body['prev_id'] == 1
        assert body['next_id'] is None

    def test_next_id_set_when_higher_detection_exists(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(db, det_id=2, crop_path='derived/2026/01/01/det0002.jpg')

        body = client.get('/api/detections/1').json()

        assert body['prev_id'] is None
        assert body['next_id'] == 2

    def test_prev_and_next_set_for_middle_detection(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)
        _insert_detection(db, det_id=2, crop_path='derived/2026/01/01/det0002.jpg')
        _insert_detection(db, det_id=3, crop_path='derived/2026/01/01/det0003.jpg')

        body = client.get('/api/detections/2').json()

        assert body['prev_id'] == 1
        assert body['next_id'] == 3

    def test_bbox_is_none_when_not_set(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        body = client.get('/api/detections/1').json()

        assert body['bbox'] is None

    def test_bbox_present_when_set(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)
        db.execute(
            '''
            UPDATE detections
            SET bbox_x = 0.1, bbox_y = 0.2, bbox_w = 0.3, bbox_h = 0.4
            WHERE id = 1
            '''
        )
        db.commit()

        body = client.get('/api/detections/1').json()

        bbox = body['bbox']
        assert abs(bbox['x'] - 0.1) < 1e-9
        assert abs(bbox['y'] - 0.2) < 1e-9
        assert abs(bbox['w'] - 0.3) < 1e-9
        assert abs(bbox['h'] - 0.4) < 1e-9

    def test_media_id_and_thumb_url_in_response(self, client, db):
        _insert_media(db)
        _insert_detection(db, det_id=1)

        body = client.get('/api/detections/1').json()

        assert body['media_id'] == 1
        assert 'thumb_url' in body

    def test_null_confidence_does_not_crash(self, client, db):
        """Human-annotated detections with null confidence must not raise TypeError."""
        _insert_media(db)
        _insert_detection(db, det_id=1, confidence=None, label_assigned_by='human')

        body = client.get('/api/detections/1').json()

        assert body['confidence'] is None


# ---------------------------------------------------------------------------
# PATCH /api/media/{media_id}/favorite
# ---------------------------------------------------------------------------

class TestSetFavorite:
    """Test the PATCH /api/media/{media_id}/favorite endpoint."""

    def test_sets_favorite_to_1(self, client, db):
        _insert_media(db)

        response = client.patch('/api/media/1/favorite', json={'favorite': 1})

        assert response.status_code == 200
        body = response.json()
        assert body['media_id'] == 1
        assert body['favorite'] == 1

    def test_clears_favorite_to_0(self, client, db):
        _insert_media(db)
        db.execute('UPDATE media SET favorite = 1 WHERE id = 1')
        db.commit()

        response = client.patch('/api/media/1/favorite', json={'favorite': 0})

        assert response.status_code == 200
        assert response.json()['favorite'] == 0

    def test_favorite_persisted_in_db(self, client, db):
        _insert_media(db)

        client.patch('/api/media/1/favorite', json={'favorite': 1})

        row = db.execute('SELECT favorite FROM media WHERE id = 1').fetchone()
        assert row['favorite'] == 1

    def test_returns_404_for_missing_media(self, client, db):
        response = client.patch('/api/media/999/favorite', json={'favorite': 1})

        assert response.status_code == 404

    def test_toggle_from_favorited_to_unfavorited_persisted(self, client, db):
        """Clearing favorite after setting it is persisted in the database."""
        _insert_media(db)
        client.patch('/api/media/1/favorite', json={'favorite': 1})

        client.patch('/api/media/1/favorite', json={'favorite': 0})

        row = db.execute('SELECT favorite FROM media WHERE id = 1').fetchone()
        assert row['favorite'] == 0
