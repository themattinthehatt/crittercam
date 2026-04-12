"""Entry point for the crittercam CLI."""

import argparse
import logging
from pathlib import Path

from crittercam.cli.cmd_classify import cmd_classify
from crittercam.cli.cmd_ingest import cmd_ingest
from crittercam.cli.cmd_serve import cmd_build_ui, cmd_serve
from crittercam.cli.cmd_setup import cmd_setup


def main() -> None:
    """Entry point for the crittercam CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
    )

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

    # ingest
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

    # serve
    serve_parser = subparsers.add_parser(
        'serve',
        help='start the web dashboard',
    )
    serve_parser.add_argument(
        '--port',
        type=int,
        default=8000,
        metavar='PORT',
        help='port for the web server (default: 8000)',
    )

    # build-ui
    subparsers.add_parser(
        'build-ui',
        help='build the React frontend for production use',
    )

    # classify
    classify_parser = subparsers.add_parser(
        'classify',
        help='run species classification on pending images',
    )
    classify_parser.add_argument(
        '--data-root',
        type=Path,
        metavar='PATH',
        help='override the data root from config',
    )
    classify_parser.add_argument(
        '--country',
        metavar='CODE',
        help='override ISO 3166-1 alpha-3 country code for geofencing (e.g. USA)',
    )
    classify_parser.add_argument(
        '--admin1-region',
        metavar='CODE',
        help='override state/province abbreviation for geofencing (e.g. CT)',
    )
    classify_parser.add_argument(
        '--crop-padding',
        type=float,
        default=0.15,
        metavar='FLOAT',
        help='fractional padding added to each side of detection bbox when cropping (default: 0.15)',
    )
    classify_parser.add_argument(
        '--retry-errors',
        action='store_true',
        help='reset previously errored detection jobs to pending before classifying',
    )
    classify_parser.add_argument(
        '--reclassify-all',
        action='store_true',
        help='reset all detection jobs (done and error) to pending before classifying',
    )

    args = parser.parse_args()

    if args.command == 'setup':
        cmd_setup()
    elif args.command == 'ingest':
        cmd_ingest(args)
    elif args.command == 'classify':
        cmd_classify(args)
    elif args.command == 'serve':
        cmd_serve(args.port)
    elif args.command == 'build-ui':
        cmd_build_ui()
