"""Ingest subcommand: copy new images from an SD card into the archive."""

import argparse
import sqlite3
import sys
from pathlib import Path

from crittercam.config import CONFIG_PATH, Config, load
from crittercam.pipeline.db import connect
from crittercam.pipeline.exif import read_exif
from crittercam.pipeline.ingest import ingest


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the ingest subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'ingest',
        help='ingest images from an SD card into the archive',
    )
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        metavar='PATH',
        help='source directory containing images to ingest',
    )
    parser.add_argument(
        '--data-root',
        type=Path,
        metavar='PATH',
        help='override the data root from config',
    )
    parser.add_argument(
        '--deployment-id',
        type=int,
        metavar='ID',
        help='deployment ID to associate with ingested files; '
             'if omitted an interactive prompt is shown',
    )
    parser.set_defaults(handler=cmd_ingest)


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest images from a source directory into the archive.

    Args:
        args: parsed command-line arguments
    """
    if args.data_root:
        config = Config(data_root=args.data_root)
    else:
        try:
            config = load(CONFIG_PATH)
        except FileNotFoundError:
            print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
            sys.exit(1)

    source = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f'Error: source directory does not exist: {source}')
        sys.exit(1)

    conn = connect(config.db_path)
    try:
        deployment_id = _resolve_deployment(conn, args.deployment_id, source_dir=source)
        if deployment_id is None:
            sys.exit(1)

        print(f'Ingesting from {source} into {config.data_root} ...')
        summary = ingest(source, config.data_root, conn, deployment_id)
    finally:
        conn.close()

    print(f'Done: {summary.ingested} ingested, {summary.skipped} skipped, {len(summary.errors)} errors.')
    for filename, reason in summary.errors.items():
        print(f'  error — {filename}: {reason}')


def _resolve_deployment(
    conn: sqlite3.Connection,
    deployment_id: int | None,
    source_dir: Path | None = None,
) -> int | None:
    """Return a validated deployment ID, prompting interactively if one was not supplied.

    If deployment_id is provided, validates it exists in the database and returns it.
    Otherwise, lists existing deployments and offers to create a new one.

    Args:
        conn: open database connection
        deployment_id: ID supplied via --deployment-id flag, or None
        source_dir: source directory of images being ingested; passed to
            _create_deployment so camera info can be pre-filled from EXIF

    Returns:
        resolved deployment ID, or None if the user aborted
    """
    if deployment_id is not None:
        row = conn.execute(
            'SELECT id FROM deployments WHERE id = :id',
            {'id': deployment_id},
        ).fetchone()
        if row is None:
            print(f'Error: no deployment with id {deployment_id}.')
            return None
        return deployment_id

    rows = conn.execute(
        'SELECT id, deployment_name, location_name, camera_make, camera_model '
        'FROM deployments ORDER BY id'
    ).fetchall()

    print()
    print('Select a deployment:')
    print()

    col_w = [4, 16, 16, 16, 16]
    header = (
        f'  {"ID":<{col_w[0]}}  '
        f'{"deployment_name":<{col_w[1]}}  '
        f'{"location_name":<{col_w[2]}}  '
        f'{"camera_make":<{col_w[3]}}  '
        f'{"camera_model":<{col_w[4]}}'
    )
    print(header)
    print('  ' + '-' * (sum(col_w) + 2 * (len(col_w) - 1)))

    for idx, row in enumerate(rows, start=1):
        def _val(v):
            return v if v is not None else ''

        print(
            f'  [{idx}] '
            f'{_val(row["id"]):<{col_w[0]}}  '
            f'{_val(row["deployment_name"]):<{col_w[1]}}  '
            f'{_val(row["location_name"]):<{col_w[2]}}  '
            f'{_val(row["camera_make"]):<{col_w[3]}}  '
            f'{_val(row["camera_model"]):<{col_w[4]}}'
        )

    new_idx = len(rows) + 1
    print(f'  [{new_idx}] Create new deployment')
    print()

    while True:
        raw = input(f'Enter choice [1-{new_idx}]: ').strip()
        if not raw.isdigit():
            print('  Please enter a number.')
            continue
        choice = int(raw)
        if choice < 1 or choice > new_idx:
            print(f'  Please enter a number between 1 and {new_idx}.')
            continue
        break

    if choice == new_idx:
        return _create_deployment(conn, source_dir=source_dir)

    return rows[choice - 1]['id']


def _create_deployment(conn: sqlite3.Connection, source_dir: Path | None = None) -> int | None:
    """Prompt the user for deployment fields, insert a new row, and return its ID.

    All fields are optional — press enter to leave any field blank. If source_dir
    is provided, camera_make and camera_model are pre-filled from the first JPEG's
    EXIF data and shown as defaults.

    Args:
        conn: open database connection
        source_dir: optional directory to scan for a sample JPEG to read camera
            make/model from EXIF

    Returns:
        ID of the newly created deployment, or None if the user aborted
    """
    camera_make_detected = None
    camera_model_detected = None
    if source_dir is not None:
        for path in source_dir.rglob('*'):
            if path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg'}:
                metadata = read_exif(path)
                camera_make_detected = metadata.camera_make
                camera_model_detected = metadata.camera_model
                break

    print()
    print('Creating new deployment (press enter to leave a field blank):')
    print()

    def _prompt(label: str, default: str | None = None) -> str | None:
        if default:
            val = input(f'  {label} [{default}]: ').strip()
            return val if val else default
        val = input(f'  {label}: ').strip()
        return val if val else None

    deployment_name = _prompt('deployment_name')
    location_name = _prompt('location_name')
    camera_make = _prompt('camera_make', camera_make_detected)
    camera_model = _prompt('camera_model', camera_model_detected)

    cursor = conn.execute(
        '''
        INSERT INTO deployments (deployment_name, location_name, camera_make, camera_model)
        VALUES (:deployment_name, :location_name, :camera_make, :camera_model)
        ''',
        {
            'deployment_name': deployment_name,
            'location_name': location_name,
            'camera_make': camera_make,
            'camera_model': camera_model,
        },
    )
    conn.commit()
    new_id = cursor.lastrowid
    print(f'  Created deployment id={new_id}.')
    return new_id
