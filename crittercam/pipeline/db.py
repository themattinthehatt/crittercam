"""Database connection, migration runner, and shared job-management utilities."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults.

    Args:
        db_path: path to the SQLite database file

    Returns:
        open connection with foreign key enforcement and row_factory set
        to sqlite3.Row for dict-style column access
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply any pending migrations to the database.

    Migrations are SQL files in the migrations/ directory named
    NNNN_description.sql, where NNNN is a zero-padded integer version
    number. Each migration is applied in order and recorded in the
    schema_migrations table. Already-applied migrations are skipped.

    Args:
        conn: open database connection
    """
    _ensure_migrations_table(conn)
    applied = _applied_versions(conn)

    pending = sorted(
        f for f in MIGRATIONS_DIR.glob('*.sql')
        if _version(f) not in applied
    )

    if not pending:
        logger.debug('no pending migrations')
        return

    for path in pending:
        version = _version(path)
        logger.info(f'applying migration {version:04d}: {path.name}')
        sql = path.read_text()
        conn.executescript(sql)
        conn.execute(
            'INSERT INTO schema_migrations (version, applied_at) VALUES (?, datetime(\'now\'))',
            (version,),
        )
        conn.commit()
        logger.info(f'migration {version:04d} applied')


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """Create the schema_migrations table if it does not exist.

    Args:
        conn: open database connection
    """
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            applied_at TEXT    NOT NULL
        )
    ''')
    conn.commit()


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    """Return the set of migration version numbers already applied.

    Args:
        conn: open database connection

    Returns:
        set of integer version numbers present in schema_migrations
    """
    rows = conn.execute('SELECT version FROM schema_migrations').fetchall()
    return {row['version'] for row in rows}


def _version(path: Path) -> int:
    """Parse the version number from a migration filename.

    Args:
        path: migration file path, e.g. 0001_initial_schema.sql

    Returns:
        integer version number

    Raises:
        ValueError: if the filename does not start with a numeric version
    """
    return int(path.stem.split('_')[0])


# ---------------------------------------------------------------------------
# Job management utilities (shared across pipeline phases)
# ---------------------------------------------------------------------------

def now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def mark_job(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    started_at: str | None = None,
    completed_at: str | None = None,
    error_msg: str | None = None,
) -> None:
    """Update a processing_jobs row's status and timestamps.

    Args:
        conn: open database connection
        job_id: primary key of the job row
        status: new status value ('running', 'done', 'error')
        started_at: ISO 8601 timestamp to set, or None to leave unchanged
        completed_at: ISO 8601 timestamp to set, or None to leave unchanged
        error_msg: error message to set, or None to leave unchanged
    """
    conn.execute(
        '''
        UPDATE processing_jobs
        SET status       = :status,
            started_at   = COALESCE(:started_at, started_at),
            completed_at = COALESCE(:completed_at, completed_at),
            error_msg    = COALESCE(:error_msg, error_msg)
        WHERE id = :job_id
        ''',
        {
            'status': status,
            'started_at': started_at,
            'completed_at': completed_at,
            'error_msg': error_msg,
            'job_id': job_id,
        },
    )


def reset_errors(conn: sqlite3.Connection, job_type: str) -> int:
    """Reset errored jobs of the given type back to pending for retry.

    Args:
        conn: open database connection
        job_type: value of processing_jobs.job_type to filter by (e.g. 'detection',
            'embedding')

    Returns:
        number of jobs reset
    """
    cursor = conn.execute(
        "UPDATE processing_jobs SET status = 'pending', started_at = NULL, "
        "completed_at = NULL, error_msg = NULL "
        "WHERE job_type = :job_type AND status = 'error'",
        {'job_type': job_type},
    )
    conn.commit()
    return cursor.rowcount


def reset_all(conn: sqlite3.Connection, job_type: str) -> int:
    """Reset all done and errored jobs of the given type back to pending.

    Args:
        conn: open database connection
        job_type: value of processing_jobs.job_type to filter by (e.g. 'detection',
            'embedding')

    Returns:
        number of jobs reset
    """
    cursor = conn.execute(
        "UPDATE processing_jobs SET status = 'pending', started_at = NULL, "
        "completed_at = NULL, error_msg = NULL "
        "WHERE job_type = :job_type AND status IN ('done', 'error')",
        {'job_type': job_type},
    )
    conn.commit()
    return cursor.rowcount
