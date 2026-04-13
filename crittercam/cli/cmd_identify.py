"""Identify subcommand: compute embeddings and assign individual identities."""

import argparse
import sys
from pathlib import Path

from crittercam.config import CONFIG_PATH, load
from crittercam.pipeline.db import connect, reset_errors


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the identify subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'identify',
        help='compute re-identification embeddings and assign individual identities',
    )
    parser.add_argument(
        '--data-root',
        type=Path,
        metavar='PATH',
        help='override the data root from config',
    )
    parser.add_argument(
        '--species',
        nargs='+',
        metavar='LEAF',
        help='restrict to one or more species leaf names (e.g. "felis catus")',
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.75,
        metavar='FLOAT',
        help='cosine similarity threshold for matching existing individuals (default: 0.75)',
    )
    parser.add_argument(
        '--retry-errors',
        action='store_true',
        help='reset previously errored embedding jobs to pending before running',
    )
    parser.add_argument(
        '--reidentify-all',
        action='store_true',
        help='clear all algorithm-assigned identities and re-run from scratch',
    )
    parser.add_argument(
        '--skip-embedding',
        action='store_true',
        help=(
            'skip embedding phase; re-run gallery matching only using existing embeddings.'
            ' Use with --threshold to explore matching without re-embedding.'
        ),
    )
    parser.set_defaults(handler=cmd_identify)


def cmd_identify(args: argparse.Namespace) -> None:
    """Compute embeddings and assign individual identities for pending detections.

    Args:
        args: parsed command-line arguments
    """
    from crittercam.pipeline.identify import (
        enqueue_pending,
        identify_pending,
        match_pending,
        reidentify_all,
        reset_assignments,
    )

    try:
        config = load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    if args.data_root:
        config.data_root = args.data_root

    conn = connect(config.db_path)
    try:
        if args.skip_embedding:
            n = reset_assignments(conn, species=args.species)
            if n:
                print(f'Cleared {n} algorithm-assigned individual(s) for re-matching.')
            summary = match_pending(
                data_root=config.data_root,
                conn=conn,
                threshold=args.threshold,
                species=args.species,
            )
        else:
            if args.reidentify_all:
                n = reidentify_all(conn, species=args.species)
                if n:
                    print(f'Reset {n} embedding job(s) to pending for full re-identification.')
            elif args.retry_errors:
                n = reset_errors(conn, job_type='embedding')
                if n:
                    print(f'Reset {n} errored embedding job(s) to pending.')

            n_enqueued = enqueue_pending(conn, species=args.species)
            if n_enqueued:
                print(f'Enqueued {n_enqueued} new embedding job(s).')

            from crittercam.identifier.megadescriptor import MegaDescriptorAdapter
            identifier = MegaDescriptorAdapter()
            summary = identify_pending(
                data_root=config.data_root,
                conn=conn,
                identifier=identifier,
                threshold=args.threshold,
                species=args.species,
            )
    finally:
        conn.close()

    if args.skip_embedding:
        print(f'Done: {summary.identified} identified.')
    else:
        print(
            f'Done: {summary.embedded} embedded, {summary.identified} identified,'
            f' {len(summary.errors)} errors.'
        )
        for filename, reason in summary.errors.items():
            print(f'  error — {filename}: {reason}')
