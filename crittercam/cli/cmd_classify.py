"""Classify subcommand: run species classification on pending images."""

import argparse
import sys

from crittercam.cli._geo import ADMIN1_RE, VALID_COUNTRY_CODES
from crittercam.config import CONFIG_PATH, load
from crittercam.pipeline.db import connect


def cmd_classify(args: argparse.Namespace) -> None:
    """Run species classification on all pending detection jobs.

    Args:
        args: parsed command-line arguments
    """
    from crittercam.classifier.speciesnet import SpeciesNetAdapter
    from crittercam.pipeline.classify import classify_pending, reset_all, reset_errors

    try:
        config = load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    if args.data_root:
        config.data_root = args.data_root

    country = args.country if args.country is not None else config.country
    admin1_region = args.admin1_region if args.admin1_region is not None else config.admin1_region

    if country is not None and country not in VALID_COUNTRY_CODES:
        print(f'Error: {country!r} is not a valid ISO 3166-1 alpha-3 country code.')
        sys.exit(1)
    if admin1_region is not None and not ADMIN1_RE.match(admin1_region):
        print(f'Error: {admin1_region!r} is not a valid state/province abbreviation.')
        sys.exit(1)

    classifier = SpeciesNetAdapter(country=country, admin1_region=admin1_region)

    conn = connect(config.db_path)
    if args.reclassify_all:
        n = reset_all(conn)
        if n:
            print(f'Reset {n} job(s) to pending for full reclassification.')
    elif args.retry_errors:
        n = reset_errors(conn)
        if n:
            print(f'Reset {n} errored job(s) to pending.')
    try:
        summary = classify_pending(
            data_root=config.data_root,
            conn=conn,
            classifier=classifier,
            crop_padding=args.crop_padding,
        )
    finally:
        conn.close()

    print(f'Done: {summary.classified} classified, {len(summary.errors)} errors.')
    for filename, reason in summary.errors.items():
        print(f'  error — {filename}: {reason}')
