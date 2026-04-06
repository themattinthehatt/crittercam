"""FastAPI route modules."""

import sqlite3

from fastapi import HTTPException

import crittercam.config as config_module
import crittercam.pipeline.db as db


def get_conn() -> sqlite3.Connection:
    """Open a database connection using the stored config.

    Returns:
        open SQLite connection

    Raises:
        HTTPException: 500 if the config file does not exist
    """
    try:
        config = config_module.load()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, detail='crittercam config not found — run crittercam setup first',
        )
    return db.connect(config.db_path)
