"""Ingest subcommand: copy new images from an SD card into the archive."""

import argparse
import sys

from crittercam.config import CONFIG_PATH, Config, load
from crittercam.pipeline.db import connect
from crittercam.pipeline.ingest import ingest


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

    print(f'Ingesting from {source} into {config.data_root} ...')
    conn = connect(config.db_path)
    try:
        summary = ingest(source, config.data_root, conn)
    finally:
        conn.close()

    print(f'Done: {summary.ingested} ingested, {summary.skipped} skipped, {len(summary.errors)} errors.')
    for filename, reason in summary.errors.items():
        print(f'  error — {filename}: {reason}')
