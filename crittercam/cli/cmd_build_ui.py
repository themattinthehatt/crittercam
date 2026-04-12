"""Build-ui subcommand: compile the React frontend for production use."""

import argparse
import subprocess
import sys
from pathlib import Path

_UI_DIR = Path(__file__).parent.parent / 'web' / 'ui'


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the build-ui subcommand.

    Args:
        subparsers: the subparsers action from the root argument parser
    """
    parser = subparsers.add_parser(
        'build-ui',
        help='build the React frontend for production use',
    )
    parser.set_defaults(handler=cmd_build_ui)


def cmd_build_ui(args: argparse.Namespace) -> None:
    """Build the React frontend for production use.

    Runs `npm run build` inside crittercam/web/ui/ and writes output to
    crittercam/web/ui/dist/, which is then served by `crittercam serve`.

    Args:
        args: parsed command-line arguments (unused; accepted for dispatch consistency)

    Raises:
        SystemExit: if npm is not found or the build fails
    """
    if not _UI_DIR.exists():
        print(f'Error: UI source directory not found at {_UI_DIR}')
        sys.exit(1)

    print(f'Building React app in {_UI_DIR} …')
    result = subprocess.run(
        ['npm', 'run', 'build'],
        cwd=_UI_DIR,
    )
    if result.returncode != 0:
        print('Error: npm run build failed.')
        sys.exit(result.returncode)

    dist_dir = _UI_DIR / 'dist'
    print(f'Build complete. Output written to {dist_dir}')
