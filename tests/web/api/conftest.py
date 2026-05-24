"""Shared fixtures for web API tests."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from crittercam.pipeline.db import connect, migrate
from crittercam.web.server import app


@pytest.fixture
def db(tmp_path):
    """Open a migrated SQLite database for API tests."""
    conn = connect(tmp_path / 'test.db')
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    """Return a TestClient with get_conn patched to return the test database.

    detections.py imports get_conn into its own namespace, so we patch it there
    rather than in the api package __init__.
    """
    db_path = Path(db.execute('PRAGMA database_list').fetchone()[2])

    def get_test_conn():
        return connect(db_path)

    with patch('crittercam.web.api.detections.get_conn', side_effect=get_test_conn):
        yield TestClient(app)
