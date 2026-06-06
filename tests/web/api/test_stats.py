"""Tests for the stats API endpoints."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from crittercam.pipeline.db import connect
from crittercam.web.server import app


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

import pytest


@pytest.fixture
def client(db):
    """Return a TestClient with stats.get_conn patched to use the test database."""
    db_path = Path(db.execute('PRAGMA database_list').fetchone()[2])

    def get_test_conn():
        return connect(db_path)

    with patch('crittercam.web.api.stats.get_conn', side_effect=get_test_conn):
        yield TestClient(app)


# ---------------------------------------------------------------------------
# date helpers — keeps tests independent of the current calendar date
# ---------------------------------------------------------------------------

RECENT = (date.today() - timedelta(days=30)).isoformat()   # within the 1-year default window
OLD    = (date.today() - timedelta(days=400)).isoformat()  # outside the 1-year default window


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

FOX   = 'abc;animalia;chordata;mammalia;carnivora;canidae;vulpes;vulpes vulpes'
CAT   = 'xyz;animalia;chordata;mammalia;carnivora;felidae;felis;domestic cat'
BLANK = 'zz;;;;;blank'

THRESHOLD = 50  # minimum detections for a species to appear in analytics results


def _insert_deployment(db, dep_id=1, deployment_name='test deployment'):
    db.execute(
        'INSERT INTO deployments (id, deployment_name) VALUES (:id, :name)',
        {'id': dep_id, 'name': deployment_name},
    )
    db.commit()


def _insert_media(db, media_id, captured_at=None, deployment_id=None):
    db.execute(
        '''
        INSERT INTO media (id, deployment_id, path, filename, ingested_at, file_hash, file_size, captured_at)
        VALUES (:id, :dep_id, :path, :fn, :ia, :fh, :fs, :ca)
        ''',
        {
            'id': media_id,
            'dep_id': deployment_id,
            'path': f'media/img{media_id:06d}.jpg',
            'fn': f'img{media_id:06d}.jpg',
            'ia': '2025-01-01T00:00:00',
            'fh': f'hash{media_id:06d}',
            'fs': 1024,
            'ca': captured_at or f'{RECENT}T10:00:00',
        },
    )


def _insert_detection(db, det_id, media_id, label=FOX):
    db.execute(
        '''
        INSERT INTO detections (id, media_id, label, confidence, crop_path,
                                label_assigned_by, created_at, is_active)
        VALUES (:id, :mid, :label, 0.9, :crop, 'algorithm', '2025-01-01T00:00:00', 1)
        ''',
        {
            'id': det_id,
            'mid': media_id,
            'label': label,
            'crop': f'derived/img{det_id:06d}_det001.jpg',
        },
    )


def _seed(db, label, n, *, base=0, captured_at=None, deployment_id=None):
    """Insert n (media, detection) pairs for one species, IDs starting from base+1."""
    for i in range(n):
        row_id = base + i + 1
        _insert_media(db, row_id, captured_at=captured_at, deployment_id=deployment_id)
        _insert_detection(db, row_id, row_id, label=label)
    db.commit()


# ---------------------------------------------------------------------------
# GET /api/stats/summary
# ---------------------------------------------------------------------------

class TestSummary:
    """Test the summary endpoint."""

    def test_returns_zeros_for_empty_db(self, client, db):
        response = client.get('/api/stats/summary')

        assert response.status_code == 200
        body = response.json()
        assert body['total_images'] == 0
        assert body['total_detections'] == 0
        assert body['species_seen'] == 0

    def test_counts_total_images(self, client, db):
        _seed(db, FOX, 3)

        body = client.get('/api/stats/summary').json()

        assert body['total_images'] == 3

    def test_counts_total_detections(self, client, db):
        _seed(db, FOX, 5)

        body = client.get('/api/stats/summary').json()

        assert body['total_detections'] == 5

    def test_counts_distinct_species(self, client, db):
        _seed(db, FOX, 2)
        _seed(db, CAT, 2, base=2)

        body = client.get('/api/stats/summary').json()

        assert body['species_seen'] == 2

    def test_species_count_excludes_blank(self, client, db):
        _seed(db, FOX, 2)
        _seed(db, BLANK, 2, base=2)

        body = client.get('/api/stats/summary').json()

        assert body['species_seen'] == 1


# ---------------------------------------------------------------------------
# GET /api/stats/detections_over_time
# ---------------------------------------------------------------------------

class TestDetectionsOverTime:
    """Test the detections_over_time endpoint."""

    def test_returns_empty_when_no_detections(self, client, db):
        response = client.get('/api/stats/detections_over_time')

        assert response.status_code == 200
        body = response.json()
        assert body['species'] == []
        assert body['data'] == []

    def test_species_below_threshold_excluded(self, client, db):
        _seed(db, FOX, THRESHOLD - 1)

        body = client.get('/api/stats/detections_over_time?date_from=2020-01-01').json()

        assert 'vulpes vulpes' not in body['species']

    def test_species_at_threshold_included(self, client, db):
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/detections_over_time?date_from=2020-01-01').json()

        assert 'vulpes vulpes' in body['species']

    def test_returns_leaf_label_not_taxonomy_path(self, client, db):
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/detections_over_time?date_from=2020-01-01').json()

        assert all(';' not in s for s in body['species'])

    def test_excludes_blank(self, client, db):
        _seed(db, BLANK, THRESHOLD)

        body = client.get('/api/stats/detections_over_time?date_from=2020-01-01').json()

        assert body['species'] == []

    def test_data_rows_have_week_key(self, client, db):
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/detections_over_time?date_from=2020-01-01').json()

        assert len(body['data']) > 0
        for row in body['data']:
            assert 'week' in row
            # strftime('%Y-%W', ...) produces 'YYYY-WW', always 7 characters
            assert len(row['week']) == 7

    def test_default_window_excludes_old_detections(self, client, db):
        """Without date_from, detections older than ~1 year are excluded."""
        _seed(db, FOX, THRESHOLD, captured_at=f'{OLD}T10:00:00')

        body = client.get('/api/stats/detections_over_time').json()

        assert 'vulpes vulpes' not in body['species']

    def test_date_from_overrides_default_window(self, client, db):
        """Explicit date_from includes detections that predate the 1-year default."""
        _seed(db, FOX, THRESHOLD, captured_at=f'{OLD}T10:00:00')
        old_year = OLD[:4]

        body = client.get(f'/api/stats/detections_over_time?date_from={old_year}-01-01').json()

        assert 'vulpes vulpes' in body['species']

    def test_date_to_excludes_detections_after_cutoff(self, client, db):
        """date_to cuts off detections that fall after the specified date."""
        _seed(db, FOX, THRESHOLD)  # data from RECENT (30 days ago)
        # cutoff is 31 days ago — one day before the data
        cutoff = (date.today() - timedelta(days=31)).isoformat()

        body = client.get(
            f'/api/stats/detections_over_time?date_from=2020-01-01&date_to={cutoff}'
        ).json()

        assert 'vulpes vulpes' not in body['species']

    def test_deployment_filter_restricts_to_one_deployment(self, client, db):
        _insert_deployment(db, dep_id=1)
        _insert_deployment(db, dep_id=2)
        _seed(db, FOX, THRESHOLD, base=0, deployment_id=1)
        _seed(db, CAT, THRESHOLD, base=THRESHOLD, deployment_id=2)

        body = client.get(
            '/api/stats/detections_over_time?deployment_id=1&date_from=2020-01-01'
        ).json()

        assert 'vulpes vulpes' in body['species']
        assert 'domestic cat' not in body['species']

    def test_deployment_filter_combined_with_date(self, client, db):
        """deployment_id and date_to can be combined — only the intersection appears."""
        _insert_deployment(db, dep_id=1)
        _seed(db, FOX, THRESHOLD, base=0, deployment_id=1)
        _seed(db, CAT, THRESHOLD, base=THRESHOLD, deployment_id=1, captured_at=f'{OLD}T10:00:00')
        old_year = OLD[:4]

        body = client.get(
            f'/api/stats/detections_over_time?deployment_id=1&date_from={old_year}-01-01'
        ).json()

        assert 'vulpes vulpes' in body['species']
        assert 'domestic cat' in body['species']

        # narrowing date_to removes the recent species
        cutoff = (date.today() - timedelta(days=31)).isoformat()
        body2 = client.get(
            f'/api/stats/detections_over_time?deployment_id=1&date_from={old_year}-01-01&date_to={cutoff}'
        ).json()
        assert 'vulpes vulpes' not in body2['species']
        assert 'domestic cat' in body2['species']


# ---------------------------------------------------------------------------
# GET /api/stats/activity_by_hour
# ---------------------------------------------------------------------------

class TestActivityByHour:
    """Test the activity_by_hour endpoint."""

    def test_returns_empty_species_and_24_hour_rows_when_no_detections(self, client, db):
        # activity_by_hour always returns 24 rows (one per hour); unlike
        # detections_over_time it does not short-circuit to an empty list.
        response = client.get('/api/stats/activity_by_hour')

        assert response.status_code == 200
        body = response.json()
        assert body['species'] == []
        assert len(body['data']) == 24
        assert all(list(row.keys()) == ['hour'] for row in body['data'])

    def test_returns_24_hour_rows(self, client, db):
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        assert len(body['data']) == 24

    def test_hour_labels_run_from_0000_to_2300(self, client, db):
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        assert body['data'][0]['hour'] == '00:00'
        assert body['data'][23]['hour'] == '23:00'

    def test_probabilities_sum_to_one(self, client, db):
        """Each species' probabilities across all 24 hours must sum to 1.0."""
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        total = sum(row.get('vulpes vulpes', 0) for row in body['data'])
        assert abs(total - 1.0) < 1e-6

    def test_hour_concentration(self, client, db):
        """All detections at 10:00 → all probability sits at hour 10, zero elsewhere."""
        _seed(db, FOX, THRESHOLD, captured_at=f'{RECENT}T10:00:00')

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        assert abs(body['data'][10]['vulpes vulpes'] - 1.0) < 1e-6
        for i, row in enumerate(body['data']):
            if i != 10:
                assert row.get('vulpes vulpes', 0) == 0.0

    def test_returns_leaf_label_not_taxonomy_path(self, client, db):
        _seed(db, FOX, THRESHOLD)

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        assert all(';' not in s for s in body['species'])

    def test_excludes_blank(self, client, db):
        _seed(db, BLANK, THRESHOLD)

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        assert body['species'] == []

    def test_species_below_threshold_excluded(self, client, db):
        _seed(db, FOX, THRESHOLD - 1)

        body = client.get('/api/stats/activity_by_hour?date_from=2020-01-01').json()

        assert 'vulpes vulpes' not in body['species']

    def test_default_window_excludes_old_detections(self, client, db):
        _seed(db, FOX, THRESHOLD, captured_at=f'{OLD}T10:00:00')

        body = client.get('/api/stats/activity_by_hour').json()

        assert 'vulpes vulpes' not in body['species']

    def test_date_from_overrides_default_window(self, client, db):
        _seed(db, FOX, THRESHOLD, captured_at=f'{OLD}T10:00:00')
        old_year = OLD[:4]

        body = client.get(f'/api/stats/activity_by_hour?date_from={old_year}-01-01').json()

        assert 'vulpes vulpes' in body['species']

    def test_deployment_filter_restricts_to_one_deployment(self, client, db):
        _insert_deployment(db, dep_id=1)
        _insert_deployment(db, dep_id=2)
        _seed(db, FOX, THRESHOLD, base=0, deployment_id=1)
        _seed(db, CAT, THRESHOLD, base=THRESHOLD, deployment_id=2)

        body = client.get(
            '/api/stats/activity_by_hour?deployment_id=1&date_from=2020-01-01'
        ).json()

        assert 'vulpes vulpes' in body['species']
        assert 'domestic cat' not in body['species']

    def test_date_to_excludes_detections_after_cutoff(self, client, db):
        _seed(db, FOX, THRESHOLD)  # data from RECENT (30 days ago)
        cutoff = (date.today() - timedelta(days=31)).isoformat()

        body = client.get(
            f'/api/stats/activity_by_hour?date_from=2020-01-01&date_to={cutoff}'
        ).json()

        assert 'vulpes vulpes' not in body['species']
