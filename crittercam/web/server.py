"""FastAPI application — entry point for the crittercam web dashboard."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

import crittercam.config as config_module
from crittercam.web.api import detections, stats

app = FastAPI(title='crittercam')

app.include_router(stats.router)
app.include_router(detections.router)


@app.get('/api/hello')
def hello() -> dict:
    """Return a greeting. Used to verify the server is running."""
    return {'message': 'hello'}


@app.get('/media/{path:path}')
def media(path: str) -> FileResponse:
    """Serve a file from the data root by its relative path.

    This is how images reach the browser — the frontend constructs a URL like
    /media/derived/2026/03/15/IMG_001_det001.jpg and the browser fetches it here.

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


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    """Serve the hand-written HTML dashboard page."""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>crittercam</title>
    <style>
        body {
            font-family: sans-serif;
            max-width: 700px;
            margin: 60px auto;
            color: #222;
        }
        h1 { margin-bottom: 0.25em; }
        .stats {
            display: flex;
            gap: 2em;
            margin-top: 1.5em;
        }
        .stat {
            text-align: center;
        }
        .stat .number {
            font-size: 3em;
            font-weight: bold;
            line-height: 1;
        }
        .stat .label {
            font-size: 0.9em;
            color: #666;
            margin-top: 0.25em;
        }
        .detection {
            margin-top: 2.5em;
            display: flex;
            gap: 1.5em;
            align-items: flex-start;
        }
        .detection img {
            width: 240px;
            height: 240px;
            object-fit: cover;
            border-radius: 6px;
            background: #eee;
        }
        .detection .meta {
            padding-top: 0.5em;
        }
        .detection .species {
            font-size: 1.4em;
            font-weight: bold;
            text-transform: capitalize;
        }
        .detection .confidence {
            color: #666;
            margin-top: 0.25em;
        }
    </style>
</head>
<body>
    <h1>crittercam</h1>
    <p>Wildlife detection dashboard</p>

    <div class="stats">
        <div class="stat">
            <div class="number" id="total-images">…</div>
            <div class="label">images</div>
        </div>
        <div class="stat">
            <div class="number" id="total-detections">…</div>
            <div class="label">detections</div>
        </div>
        <div class="stat">
            <div class="number" id="species-seen">…</div>
            <div class="label">species</div>
        </div>
    </div>

    <div class="detection">
        <img id="crop-img" src="" alt="detection crop">
        <div class="meta">
            <div class="species" id="species-label">…</div>
            <div class="confidence" id="confidence">…</div>
        </div>
    </div>

    <script>
        // First fetch: summary stats (same as Step 3)
        fetch('/api/stats/summary')
            .then(response => response.json())
            .then(data => {
                document.getElementById('total-images').textContent = data.total_images;
                document.getElementById('total-detections').textContent = data.total_detections;
                document.getElementById('species-seen').textContent = data.species_seen;
            });

        // Second fetch: the first detection.
        // The API returns crop_url — a path like /media/derived/2026/03/15/IMG_001_det001.jpg.
        // Setting img.src to that URL causes the browser to fire a third HTTP request
        // to fetch the actual image bytes. The server handles that at GET /media/{path}.
        fetch('/api/detections/first')
            .then(response => response.json())
            .then(data => {
                document.getElementById('crop-img').src = data.crop_url;
                document.getElementById('species-label').textContent = data.label;
                document.getElementById('confidence').textContent =
                    'confidence: ' + (data.confidence * 100).toFixed(1) + '%';
            });
    </script>
</body>
</html>
'''
