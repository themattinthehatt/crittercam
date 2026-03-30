"""Command-line interface for crittercam."""

import argparse
import re
import sys
from pathlib import Path

from crittercam.config import CONFIG_PATH, Config, load, save
from crittercam.pipeline.db import connect, migrate
from crittercam.pipeline.ingest import ingest

# ISO 3166-1 alpha-3 codes accepted by SpeciesNet for geofencing.
_VALID_COUNTRY_CODES = frozenset({
    'ABW', 'AFG', 'AGO', 'AIA', 'ALA', 'ALB', 'AND', 'ARE', 'ARG', 'ARM',
    'ASM', 'ATA', 'ATF', 'ATG', 'AUS', 'AUT', 'AZE', 'BDI', 'BEL', 'BEN',
    'BES', 'BFA', 'BGD', 'BGR', 'BHR', 'BHS', 'BIH', 'BLM', 'BLR', 'BLZ',
    'BMU', 'BOL', 'BRA', 'BRB', 'BRN', 'BTN', 'BVT', 'BWA', 'CAF', 'CAN',
    'CCK', 'CHE', 'CHL', 'CHN', 'CIV', 'CMR', 'COD', 'COG', 'COK', 'COL',
    'COM', 'CPV', 'CRI', 'CUB', 'CUW', 'CXR', 'CYM', 'CYP', 'CZE', 'DEU',
    'DJI', 'DMA', 'DNK', 'DOM', 'DZA', 'ECU', 'EGY', 'ERI', 'ESH', 'ESP',
    'EST', 'ETH', 'FIN', 'FJI', 'FLK', 'FRA', 'FRO', 'FSM', 'GAB', 'GBR',
    'GEO', 'GGY', 'GHA', 'GIB', 'GIN', 'GLP', 'GMB', 'GNB', 'GNQ', 'GRC',
    'GRD', 'GRL', 'GTM', 'GUF', 'GUM', 'GUY', 'HKG', 'HMD', 'HND', 'HRV',
    'HTI', 'HUN', 'IDN', 'IMN', 'IND', 'IOT', 'IRL', 'IRN', 'IRQ', 'ISL',
    'ISR', 'ITA', 'JAM', 'JEY', 'JOR', 'JPN', 'KAZ', 'KEN', 'KGZ', 'KHM',
    'KIR', 'KNA', 'KOR', 'KWT', 'LAO', 'LBN', 'LBR', 'LBY', 'LCA', 'LIE',
    'LKA', 'LSO', 'LTU', 'LUX', 'LVA', 'MAC', 'MAF', 'MAR', 'MCO', 'MDA',
    'MDG', 'MDV', 'MEX', 'MHL', 'MKD', 'MLI', 'MLT', 'MMR', 'MNE', 'MNG',
    'MNP', 'MOZ', 'MRT', 'MSR', 'MTQ', 'MUS', 'MWI', 'MYS', 'MYT', 'NAM',
    'NCL', 'NER', 'NFK', 'NGA', 'NIC', 'NIU', 'NLD', 'NOR', 'NPL', 'NRU',
    'NZL', 'OMN', 'PAK', 'PAN', 'PCN', 'PER', 'PHL', 'PLW', 'PNG', 'POL',
    'PRI', 'PRK', 'PRT', 'PRY', 'PSE', 'PYF', 'QAT', 'REU', 'ROU', 'RUS',
    'RWA', 'SAU', 'SDN', 'SEN', 'SGP', 'SGS', 'SHN', 'SJM', 'SLB', 'SLE',
    'SLV', 'SMR', 'SOM', 'SPM', 'SRB', 'SSD', 'STP', 'SUR', 'SVK', 'SVN',
    'SWE', 'SWZ', 'SXM', 'SYC', 'SYR', 'TCA', 'TCD', 'TGO', 'THA', 'TJK',
    'TKL', 'TKM', 'TLS', 'TON', 'TTO', 'TUN', 'TUR', 'TUV', 'TWN', 'TZA',
    'UGA', 'UKR', 'UMI', 'URY', 'USA', 'UZB', 'VAT', 'VCT', 'VEN', 'VGB',
    'VIR', 'VNM', 'VUT', 'WLF', 'WSM', 'YEM', 'ZAF', 'ZMB', 'ZWE',
})

# admin1_region: state/province abbreviation, e.g. 'CT', 'CA', 'ON'
_ADMIN1_RE = re.compile(r'^[A-Z0-9]{1,8}$')


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

    args = parser.parse_args()

    if args.command == 'setup':
        cmd_setup()
    elif args.command == 'ingest':
        cmd_ingest(args)
    elif args.command == 'classify':
        cmd_classify(args)


def cmd_setup() -> None:
    """Prompt for configuration values, write config, and initialise the database."""
    if CONFIG_PATH.exists():
        existing = load(CONFIG_PATH)
        print(f'Config already exists at {CONFIG_PATH}')
        print(f'Current data root: {existing.data_root}')
        answer = input('Overwrite? [y/N] ').strip().lower()
        if answer != 'y':
            print('Aborted.')
            sys.exit(0)

    data_root_str = input(
        'Enter data root directory (where images and database will be stored): '
    ).strip()
    if not data_root_str:
        print('Error: data root cannot be empty.')
        sys.exit(1)
    data_root = Path(data_root_str).expanduser().resolve()

    country = _prompt_country()
    admin1_region = _prompt_admin1_region() if country else None

    config = Config(data_root=data_root, country=country, admin1_region=admin1_region)
    save(config, CONFIG_PATH)
    print(f'Config written to {CONFIG_PATH}')

    print(f'Initialising database at {config.db_path} ...')
    conn = connect(config.db_path)
    migrate(conn)
    conn.close()
    print('Done.')


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


def cmd_classify(args: argparse.Namespace) -> None:
    """Run species classification on all pending detection jobs.

    Args:
        args: parsed command-line arguments
    """
    from crittercam.classifier.speciesnet import SpeciesNetAdapter
    from crittercam.pipeline.classify import classify_pending

    try:
        config = load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    if args.data_root:
        config.data_root = args.data_root

    country = args.country if args.country is not None else config.country
    admin1_region = args.admin1_region if args.admin1_region is not None else config.admin1_region

    if country is not None and country not in _VALID_COUNTRY_CODES:
        print(f'Error: {country!r} is not a valid ISO 3166-1 alpha-3 country code.')
        sys.exit(1)
    if admin1_region is not None and not _ADMIN1_RE.match(admin1_region):
        print(f'Error: {admin1_region!r} is not a valid state/province abbreviation.')
        sys.exit(1)

    classifier = SpeciesNetAdapter(country=country, admin1_region=admin1_region)

    conn = connect(config.db_path)
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


def _prompt_country() -> str | None:
    """Prompt for an ISO 3166-1 alpha-3 country code with validation.

    Returns:
        validated country code, or None if the user skips
    """
    while True:
        raw = input(
            'Enter country code for SpeciesNet geofencing (ISO 3166-1 alpha-3, e.g. USA) '
            '[leave blank to skip]: '
        ).strip().upper()
        if not raw:
            return None
        if raw in _VALID_COUNTRY_CODES:
            return raw
        print(f'  {raw!r} is not a recognised ISO 3166-1 alpha-3 code. Try again.')


def _prompt_admin1_region() -> str | None:
    """Prompt for a state/province abbreviation with format validation.

    Returns:
        validated admin1 region code, or None if the user skips
    """
    while True:
        raw = input(
            'Enter state/province abbreviation (e.g. CT for Connecticut) '
            '[leave blank to skip]: '
        ).strip().upper()
        if not raw:
            return None
        if _ADMIN1_RE.match(raw):
            return raw
        print(f'  {raw!r} is not a valid abbreviation. Use 1–8 uppercase letters/digits.')
