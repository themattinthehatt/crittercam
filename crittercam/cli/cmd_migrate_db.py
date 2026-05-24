"""migrate-db subcommand: apply pending database migrations."""

import argparse

import crittercam.config as config_module
from crittercam.pipeline.db import connect, migrate


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the migrate-db subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'migrate-db',
        help='apply any pending database migrations',
    )
    parser.set_defaults(handler=cmd_migrate_db)


def cmd_migrate_db(args: argparse.Namespace | None = None) -> None:
    """Load the existing config and apply any pending migrations."""
    config = config_module.load()
    print(f'Migrating database at {config.db_path} ...')
    conn = connect(config.db_path)
    migrate(conn)
    conn.close()
    print('Done.')
