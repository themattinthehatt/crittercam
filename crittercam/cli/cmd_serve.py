"""Serve and build-ui subcommands for the crittercam web dashboard."""

import subprocess
import sys
import webbrowser
from pathlib import Path

from crittercam.config import CONFIG_PATH, load

# path to the React source, relative to this file's package root
_UI_DIR = Path(__file__).parent.parent / 'web' / 'ui'


def cmd_serve(port: int) -> None:
    """Start the crittercam web dashboard.

    Loads config, mounts the built React app if present, opens the browser,
    and runs Uvicorn on the requested port.

    Args:
        port: TCP port on which Uvicorn will listen
    """
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


def cmd_build_ui() -> None:
    """Build the React frontend for production use.

    Runs `npm run build` inside crittercam/web/ui/ and writes output to
    crittercam/web/ui/dist/, which is then served by `crittercam serve`.

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
