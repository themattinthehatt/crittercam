# Phase 4 — Web Interface Implementation Plan

A learning-oriented build plan. Each step introduces one new concept, produces
something visible and runnable, and leaves the app in a working state. Steps 1–4
deliberately avoid React so the raw HTTP/JS mechanics are visible before any
framework takes over.

---

## Group A — The server, standing alone ✓

**Step 1: A single FastAPI endpoint** ✓
Add `fastapi` and `uvicorn` to the project, create `crittercam/web/server.py` with
one endpoint: `GET /api/hello` returning `{"message": "hello"}`. Run uvicorn manually
and visit it in the browser.
*Learns: what a web server is, what an HTTP GET request is, what JSON over HTTP looks
like. Also visit `/docs` — FastAPI gives you an interactive API explorer for free.*

**Step 2: A real endpoint backed by the database** ✓
Add `GET /api/stats/summary` returning `{"total_images": N, "total_detections": N,
"species_seen": N}`. This requires reading the config and querying SQLite — both
things you already know how to do.
*Learns: how a real endpoint connects to your data. Nothing new on the web side —
just Python you already understand.*

---

## Group B — The browser, without React ✓

**Step 3: A hand-written HTML page** ✓
Add a `GET /` route that returns a raw HTML string. That HTML includes a `<script>`
block that calls `fetch('/api/stats/summary')` and writes the numbers into the page.
*Learns: HTML structure, what JavaScript is, how `fetch()` and `async/await` work,
how the browser executes JS and modifies the page — the raw mechanics before any
framework.*

**Step 4: Serving an image over HTTP** ✓
Add a media-serving route (FastAPI `FileResponse`) that serves image files from
`data_root`. Add `GET /api/detections/first` returning one detection row. Display
the detection crop `<img>` in the HTML page alongside its label and confidence.
*Learns: how image files are delivered over HTTP, `<img>` tags, how data from the
API flows into HTML.*

---

## Group C — Introducing React and Vite ✓

**Step 5: Set up Vite + the dev proxy** ✓
Scaffold the React app with `npm create vite@latest` inside `crittercam/web/ui/`.
Get the default Vite "Hello World" running. Configure `vite.config.js` to proxy
`/api/*` to `localhost:8000`. Set up `Procfile.dev` to start both servers with one
command.
*Learns: what npm/Node.js are (package manager + runtime, analogous to pip +
python), what Vite does (bundles and hot-reloads JS, like a dev server), what a
proxy is and why it's needed.*

**Step 6: First React component with live data** ✓
Replace the static HTML with a `StatsBar` React component. It calls
`/api/stats/summary` via `fetch` and renders the counts. Introduce `useState` and
`useEffect`.
*Learns: what a React component is (a function that returns HTML-like JSX), what
state is (the component's memory), how `useEffect` triggers data fetching when the
component mounts — the React equivalent of "run this code once on startup".*

---

## Group D — Building the Browse tab ✓

**Step 7: Previous/Next through a single image** ✓
Add `GET /api/detections/:id` returning one detection's crop, full image, label,
confidence, and `prev_id`/`next_id`. A React component shows the crop image and two
arrow buttons. Clicking next loads the next detection.
*Learns: how state changes trigger re-renders (the core React loop), how to pass
data between a component's state and the API.*

**Step 8: A thumbnail grid** ✓
Add `GET /api/detections` returning the first 24 detections. Render them as a CSS
grid of `<img>` thumbnails using `.map()`.
*Learns: how to render a list of items in React, basic CSS Grid layout.*

**Step 9: Pagination** ✓
Add `page` and `page_size` query parameters to `GET /api/detections`. Add page
number controls to the grid component.
*Learns: query parameters in API design, how changing state (current page number)
triggers a new fetch and re-render.*

**Step 10: Detail panel on click** ✓
Clicking a thumbnail shows a side panel with the detection crop, the full image, a
bounding box drawn as an SVG overlay, and the metadata fields.
*Learns: event handlers, conditional rendering, SVG overlays (a clean way to draw
on top of images).*

**Step 11: Species and date filters** ✓
Add a species dropdown and a date range input above the grid. Selecting a filter
re-fetches with the new parameters appended to the URL. Update the API to support
`species`, `date_from`, `date_to` query params.
*Learns: controlled inputs in React, how filter state feeds into the API query
string.*

---

## Group E — Home tab and tab navigation

**Step 12: Home tab**
Add `GET /api/stats/recent_crops` (last N detection crops) and
`GET /api/stats/detections_over_time`. Build the Home tab: summary numbers from
Step 2, a strip of recent crop thumbnails, a Recharts bar chart.
*Learns: Recharts (just a React component that takes data as props), multiple
parallel fetches from one component.*

**Step 13: Three-tab layout**
Wire up tab navigation: Home, Browse, Analytics (placeholder). Tab state lives in
the top-level `App` component and conditionally renders the right tab content.
*Learns: lifting state up (the App component owns the active tab; child components
react to it), component composition.*

---

## Group F — CLI integration and production build

**Step 14: `crittercam serve` CLI command**
Add `crittercam/cli/cmd_serve.py` that starts Uvicorn and auto-opens the browser.
*Learns: how to launch a subprocess from Python (or use uvicorn's Python API
directly), `webbrowser.open()`.*

**Step 15: `crittercam build-ui` and production static file serving**
Add `crittercam build-ui` to run `npm run build`. Mount the `dist/` output in
FastAPI as `StaticFiles` so one server handles everything in production.
*Learns: what "building" a frontend means (bundling JS into a few optimized files),
how FastAPI serves static files, the difference between dev and production mode.*
