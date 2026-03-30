"""Setup subcommand: configure crittercam and initialise the database."""

import sys
from pathlib import Path

from crittercam.cli._geo import prompt_admin1_region, prompt_country
from crittercam.config import CONFIG_PATH, Config, load, save
from crittercam.pipeline.db import connect, migrate


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

    country = prompt_country()
    admin1_region = prompt_admin1_region() if country else None

    config = Config(data_root=data_root, country=country, admin1_region=admin1_region)
    save(config, CONFIG_PATH)
    print(f'Config written to {CONFIG_PATH}')

    print(f'Initialising database at {config.db_path} ...')
    conn = connect(config.db_path)
    migrate(conn)
    conn.close()
    print('Done.')
