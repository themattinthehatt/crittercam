"""Serve subcommand: start the crittercam web dashboard."""

import argparse
import sys
import webbrowser
from pathlib import Path

from crittercam.config import CONFIG_PATH, load

_UI_DIR = Path(__file__).parent.parent / 'web' / 'ui'


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the serve subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'serve',
        help='start the web dashboard',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        metavar='PORT',
        help='port for the web server (default: 8000)',
    )
    parser.set_defaults(handler=cmd_serve)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the crittercam web dashboard.

    Loads config, mounts the built React app if present, opens the browser,
    and runs Uvicorn on the requested port.

    Args:
        args: parsed command-line arguments
    """
    port = args.port
    try:
        load(CONFIG_PATH)
    except FileNotFoundError:
        print(f'Error: no config file found at {CONFIG_PATH}. Run `crittercam setup` first.')
        sys.exit(1)

    dist_dir = _UI_DIR / 'dist'
    if not dist_dir.exists():
        print(
            'Warning: built UI not found. Run `crittercam build-ui` first, '
            'or use the dev server (see Procfile.dev).'
        )

    url = f'http://localhost:{port}'
    webbrowser.open(url)

    import uvicorn
    uvicorn.run(
        'crittercam.web.server:app',
        host='0.0.0.0',
        port=port,
        reload=False,
    )
