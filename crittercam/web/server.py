"""FastAPI application — entry point for the crittercam web dashboard."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import crittercam.config as config_module
from crittercam.web.api import detections, stats

app = FastAPI(title='crittercam')

app.include_router(stats.router)
app.include_router(detections.router)

# mount built React app if present; skipped in development (Vite serves the UI)
_DIST_DIR = Path(__file__).parent / 'ui' / 'dist'
if _DIST_DIR.exists():
    app.mount('/', StaticFiles(directory=_DIST_DIR, html=True), name='ui')


@app.get('/media/{path:path}')
def media(path: str) -> FileResponse:
    """Serve a file from the data root by its relative path.

    The frontend constructs URLs like /media/derived/YYYY/MM/DD/file.jpg;
    this route resolves them against data_root and streams the file.

    Args:
        path: relative path from data_root (e.g. derived/YYYY/MM/DD/file.jpg)

    Returns:
        the file as a binary HTTP response

    Raises:
        HTTPException: 404 if the file does not exist
    """
    try:
        config = config_module.load()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='crittercam config not found')

    full_path = config.data_root / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f'file not found: {path}')

    return FileResponse(full_path)
