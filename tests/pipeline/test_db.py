"""Tests for crittercam.pipeline.db."""

import sqlite3
from pathlib import Path

import pytest

from crittercam.pipeline.db import (
    _applied_versions,
    _ensure_migrations_table,
    _version,
    connect,
    migrate,
)


@pytest.fixture
def raw_db(tmp_path):
    """Open a bare database connection with no migrations applied."""
    conn = connect(tmp_path / 'test.db')
    yield conn
    conn.close()


@pytest.fixture
def migration_dir(tmp_path):
    """Return a temporary directory for migration files."""
    d = tmp_path / 'migrations'
    d.mkdir()
    return d


class TestConnect:
    """Test the connect function."""

    def test_connect_creates_parent_dirs(self, tmp_path):
        # Arrange
        db_path = tmp_path / 'nested' / 'dir' / 'test.db'

        # Act
        conn = connect(db_path)
        conn.close()

        # Assert
        assert db_path.exists()

    def test_connect_enables_foreign_keys(self, tmp_path):
        # Arrange / Act
        conn = connect(tmp_path / 'test.db')

        # Assert
        row = conn.execute('PRAGMA foreign_keys').fetchone()
        assert row[0] == 1
        conn.close()

    def test_connect_sets_row_factory(self, tmp_path):
        # Arrange / Act
        conn = connect(tmp_path / 'test.db')
        conn.execute('CREATE TABLE t (x INTEGER)')
        conn.execute('INSERT INTO t VALUES (42)')

        # Assert — row_factory allows column access by name
        row = conn.execute('SELECT x FROM t').fetchone()
        assert row['x'] == 42
        conn.close()


class TestEnsureMigrationsTable:
    """Test the _ensure_migrations_table function."""

    def test_creates_table_when_absent(self, raw_db):
        # Act
        _ensure_migrations_table(raw_db)

        # Assert
        row = raw_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        assert row is not None

    def test_idempotent(self, raw_db):
        # Act — calling twice must not raise
        _ensure_migrations_table(raw_db)
        _ensure_migrations_table(raw_db)


class TestAppliedVersions:
    """Test the _applied_versions function."""

    def test_empty_when_no_migrations(self, raw_db):
        # Arrange
        _ensure_migrations_table(raw_db)

        # Act / Assert
        assert _applied_versions(raw_db) == set()

    def test_returns_applied_versions(self, raw_db):
        # Arrange
        _ensure_migrations_table(raw_db)
        raw_db.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (1, '2026-01-01')"
        )
        raw_db.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (3, '2026-01-02')"
        )
        raw_db.commit()

        # Act / Assert
        assert _applied_versions(raw_db) == {1, 3}


class TestVersion:
    """Test the _version function."""

    def test_parses_version_number(self, tmp_path):
        # Arrange
        path = tmp_path / '0001_initial_schema.sql'

        # Act / Assert
        assert _version(path) == 1

    def test_parses_large_version(self, tmp_path):
        # Arrange
        path = tmp_path / '0042_add_weather_label.sql'

        # Act / Assert
        assert _version(path) == 42


class TestMigrate:
    """Test the migrate function."""

    def test_applies_migrations_to_fresh_database(self, raw_db):
        # Act
        migrate(raw_db)

        # Assert — all three tables from 0001 exist
        tables = {
            row['name']
            for row in raw_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {'images', 'detections', 'processing_jobs'}.issubset(tables)

    def test_records_applied_version(self, raw_db):
        # Act
        migrate(raw_db)

        # Assert
        assert 1 in _applied_versions(raw_db)

    def test_idempotent_on_already_migrated_database(self, raw_db):
        # Act — run twice
        migrate(raw_db)
        migrate(raw_db)

        # Assert — version recorded exactly once
        rows = raw_db.execute('SELECT version FROM schema_migrations').fetchall()
        versions = [row['version'] for row in rows]
        assert versions.count(1) == 1

    def test_applies_migrations_in_order(self, raw_db, tmp_path, monkeypatch):
        # Arrange — two migrations; second depends on first
        mig_dir = tmp_path / 'migrations'
        mig_dir.mkdir()
        (mig_dir / '0001_create_foo.sql').write_text(
            'CREATE TABLE foo (id INTEGER PRIMARY KEY);'
        )
        (mig_dir / '0002_add_bar.sql').write_text(
            'ALTER TABLE foo ADD COLUMN bar TEXT;'
        )
        monkeypatch.setattr('crittercam.pipeline.db.MIGRATIONS_DIR', mig_dir)

        # Act
        migrate(raw_db)

        # Assert — both applied
        assert _applied_versions(raw_db) == {1, 2}
        cols = {row['name'] for row in raw_db.execute('PRAGMA table_info(foo)')}
        assert 'bar' in cols

    def test_skips_already_applied_migrations(self, raw_db, tmp_path, monkeypatch):
        # Arrange — pre-seed version 1 as applied
        mig_dir = tmp_path / 'migrations'
        mig_dir.mkdir()
        (mig_dir / '0001_noop.sql').write_text(
            'CREATE TABLE should_not_exist (id INTEGER PRIMARY KEY);'
        )
        monkeypatch.setattr('crittercam.pipeline.db.MIGRATIONS_DIR', mig_dir)
        _ensure_migrations_table(raw_db)
        raw_db.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (1, '2026-01-01')"
        )
        raw_db.commit()

        # Act
        migrate(raw_db)

        # Assert — table was not created (migration was skipped)
        row = raw_db.execute(
            "SELECT name FROM sqlite_master WHERE name='should_not_exist'"
        ).fetchone()
        assert row is None
