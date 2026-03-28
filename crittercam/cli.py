"""Command-line interface for crittercam."""

import argparse
import sys
from pathlib import Path

from crittercam.config import CONFIG_PATH, Config, load, save
from crittercam.pipeline.db import connect, migrate


def main() -> None:
    """Entry point for the crittercam CLI."""
    parser = argparse.ArgumentParser(
        prog='crittercam',
        description='Backyard wildlife camera trap pipeline.',
    )
    subparsers = parser.add_subparsers(dest='command', metavar='command')
    subparsers.required = True

    # setup
    subparsers.add_parser(
        'setup',
        help='configure crittercam and initialise the database',
    )

    # ingest (stub for now)
    ingest_parser = subparsers.add_parser(
        'ingest',
        help='ingest images from an SD card into the archive',
    )
    ingest_parser.add_argument(
        '--source',
        type=Path,
        required=True,
        metavar='PATH',
        help='source directory containing images to ingest',
    )
    ingest_parser.add_argument(
        '--data-root',
        type=Path,
        metavar='PATH',
        help='override the data root from config',
    )

    args = parser.parse_args()

    if args.command == 'setup':
        cmd_setup()
    elif args.command == 'ingest':
        cmd_ingest(args)


def cmd_setup() -> None:
    """Prompt for data_root, write config, and initialise the database."""
    if CONFIG_PATH.exists():
        existing = load(CONFIG_PATH)
        print(f'Config already exists at {CONFIG_PATH}')
        print(f'Current data root: {existing.data_root}')
        answer = input('Overwrite? [y/N] ').strip().lower()
        if answer != 'y':
            print('Aborted.')
            sys.exit(0)

    data_root_str = input('Enter data root directory (where images and database will be stored): ').strip()
    if not data_root_str:
        print('Error: data root cannot be empty.')
        sys.exit(1)

    data_root = Path(data_root_str).expanduser().resolve()
    config = Config(data_root=data_root)
    save(config, CONFIG_PATH)
    print(f'Config written to {CONFIG_PATH}')

    print(f'Initialising database at {config.db_path} ...')
    conn = connect(config.db_path)
    migrate(conn)
    conn.close()
    print('Done.')


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest images from a source directory (stub).

    Args:
        args: parsed command-line arguments
    """
    # resolve data_root: CLI flag overrides config
    if args.data_root:
        config = Config(data_root=args.data_root)
    else:
        try:
            config = load()
        except FileNotFoundError:
            print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
            sys.exit(1)

    print(f'Ingesting from {args.source} into {config.data_root} ...')
    print('(ingest not yet implemented)')
