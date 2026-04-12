"""Clean-db subcommand: remove unwanted detections and their associated images and files."""

import argparse
import sys

from crittercam.config import CONFIG_PATH, load
from crittercam.pipeline.clean import find_targets, delete_targets
from crittercam.pipeline.db import connect


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the clean-db subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'clean-db',
        help='remove unwanted detections and their parent images from the database and disk',
    )
    parser.add_argument(
        '--labels',
        nargs='+',
        required=True,
        metavar='LABEL',
        help='one or more leaf label names to remove (e.g. --labels human blank); '
             'matched against the final segment of the stored taxonomy string',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='show what would be deleted without making any changes',
    )
    parser.set_defaults(handler=cmd_clean_db)


def cmd_clean_db(args: argparse.Namespace) -> None:
    """Remove detections matching the given labels along with their parent images and files.

    Queries active detections whose label matches any of the provided labels, then
    permanently deletes: detection rows (active and inactive), image rows, processing
    job rows, detection crops, thumbnails, and raw image files.

    Args:
        args: parsed command-line arguments
    """
    try:
        config = load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    labels = [label.lower() for label in args.labels]

    conn = connect(config.db_path)
    try:
        targets = find_targets(conn, labels)

        if not targets:
            print(f'No active detections found with labels: {", ".join(labels)}')
            return

        n_detections = len(targets)
        n_images = len({t.image_id for t in targets})
        print(
            f'Found {n_detections} active detection(s) across {n_images} image(s) '
            f'matching: {", ".join(labels)}'
        )

        if args.dry_run:
            print('Dry run — no changes made.')
            return

        answer = input(
            f'Permanently delete {n_detections} detection(s), {n_images} image(s), '
            f'and all associated files? [y/N] '
        ).strip().lower()
        if answer != 'y':
            print('Aborted.')
            return

        summary = delete_targets(config.data_root, conn, targets)
    finally:
        conn.close()

    total_files = summary.raw_images_deleted + summary.thumbnails_deleted + summary.crops_deleted
    print(
        f'Done: removed {summary.detections} detection(s) and {summary.images} image(s) '
        f'from the database, and deleted {total_files} files from disk '
        f'({summary.raw_images_deleted} raw, {summary.thumbnails_deleted} thumbnails, '
        f'{summary.crops_deleted} crops).'
    )
    if summary.files_missing:
        print(f'  Warning: {summary.files_missing} expected file(s) not found on disk.')
