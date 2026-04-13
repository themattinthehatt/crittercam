"""merge-individuals subcommand: merge a set of individual ids into one."""

import argparse
import sys

from crittercam.config import CONFIG_PATH, load
from crittercam.pipeline.db import connect


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the merge-individuals subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'merge-individuals',
        help='merge multiple individuals into the one with the lowest id',
    )
    parser.add_argument(
        'ids',
        nargs='+',
        type=int,
        metavar='ID',
        help='individual ids to merge (at least two required)',
    )
    parser.set_defaults(handler=cmd_merge_individuals)


def cmd_merge_individuals(args: argparse.Namespace) -> None:
    """Merge the given individual ids into the lowest id in the list.

    All detections belonging to any of the supplied individuals are reassigned
    to the lowest id and marked as human-assigned. The other individual rows
    are deleted.

    Args:
        args: parsed command-line arguments
    """
    from crittercam.pipeline.identify import merge_individuals

    if len(args.ids) < 2:
        print('Error: merge-individuals requires at least two ids.')
        sys.exit(1)

    try:
        config = load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    conn = connect(config.db_path)
    try:
        target = merge_individuals(conn, args.ids)
    except ValueError as exc:
        print(f'Error: {exc}')
        sys.exit(1)
    finally:
        conn.close()

    others = sorted(v for v in args.ids if v != target)
    print(f'Merged {", ".join(f"#{i}" for i in others)} → #{target}.')
