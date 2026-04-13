"""name-individual subcommand: assign or update a nickname for an individual."""

import argparse
import sys

from crittercam.config import CONFIG_PATH, load
from crittercam.pipeline.db import connect


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the name-individual subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'name-individual',
        help='assign or update a nickname for an individual',
    )
    parser.add_argument('individual_id', type=int, metavar='ID', help='individual id')
    parser.add_argument('nickname', metavar='NICKNAME', help='display name to assign')
    parser.set_defaults(handler=cmd_name_individual)


def cmd_name_individual(args: argparse.Namespace) -> None:
    """Assign or update the nickname for an individual.

    Args:
        args: parsed command-line arguments
    """
    from crittercam.pipeline.identify import name_individual

    try:
        config = load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    conn = connect(config.db_path)
    try:
        name_individual(conn, args.individual_id, args.nickname)
    except ValueError as exc:
        print(f'Error: {exc}')
        sys.exit(1)
    finally:
        conn.close()

    print(f'#{args.individual_id} → "{args.nickname}".')
