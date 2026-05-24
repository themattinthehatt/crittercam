# Contributing

## Production environment setup

### 1. Create a conda environment

```bash
conda create -n crittercam python=3.12
conda activate crittercam
```

### 2. Install the package

From the repo root:

```bash
pip install -e ".[dev]"
```

The `-e` flag installs in editable mode so code changes take effect immediately without reinstalling.

### 3. Run the tests

```bash
pytest
```

### 4. Install Node.js (for the web dashboard and Storybook)

Node.js v22+ is required. Tailwind CSS's native binary (`@tailwindcss/oxide`) must be compiled with the same Node version used to run the app — mismatches cause startup failures.

Install via [nvm](https://github.com/nvm-sh/nvm):

```bash
nvm install 22
nvm use 22
```

Or install via conda:

```bash
conda install -n critter -c conda-forge "nodejs>=22"
```

Verify the install:

```bash
node --version   # should print v22 or later
npm --version
```

### 5. Install frontend dependencies

**Important:** run this with Node 22 active. If you previously installed with an older Node version, delete `node_modules` and `package-lock.json` first to force a clean recompile of native binaries:

```bash
cd crittercam/web/ui && rm -rf node_modules package-lock.json && npm install
```

Otherwise, from the repo root:

```bash
npm --prefix crittercam/web/ui install
```

This downloads all frontend packages into `crittercam/web/ui/node_modules/`. Only needed once (and again after pulling changes that update `package.json`).

---

## Dev environment setup

Storybook requires Node.js v22+. If you installed an older version above, upgrade before proceeding:

```bash
nvm install 22 && nvm use 22
```

### 1. Install honcho (dev process manager)

```bash
pip install honcho
```

Honcho reads `Procfile.dev` and starts the API server and Vite dev server together with one command.

### 2. Run the dev server

```bash
honcho start -f Procfile.dev
```

This starts two processes simultaneously:
- FastAPI/Uvicorn on `http://localhost:8000` — the API
- Vite on `http://localhost:5173` — the UI (visit this in the browser)

Vite automatically forwards `/api/*` and `/media/*` requests to the FastAPI server, so the browser only needs to know about port 5173.

### 3. Run Storybook

Storybook is a tool for building and reviewing UI components in isolation — no running API server or populated database required.

On Linux, Playwright (used by Storybook's test runner) requires system dependencies. Install them once:

```bash
npx --prefix crittercam/web/ui playwright install chromium --with-deps
```

Then start Storybook:

```bash
npm --prefix crittercam/web/ui run storybook
```

Then open `http://localhost:6006` in the browser. The main dashboard and Storybook can run simultaneously on their separate ports (5173 and 6006).

Component files and their story files live together in `crittercam/web/ui/src/components/`. See `design/STORYBOOK.md` for the component inventory and development workflow.

### 4. Run frontend tests

Interactive components have `play` functions in their story files that verify callback behaviour (clicks fire the right handlers, `stopPropagation` holds, confirmation dialogs appear and dismiss correctly). Run them headlessly from the repo root:

```bash
conda run -n critter npx --prefix crittercam/web/ui vitest run
```

This launches a headless Chromium browser via Playwright, renders each story, executes any `play` function, and reports pass/fail — no running API server required. A clean run currently takes around 5 seconds.

To debug a failing interaction visually, open Storybook (`npm --prefix crittercam/web/ui run storybook`), navigate to the story, and inspect the **Interactions** panel at the bottom of the canvas.

Stories without a `play` function still run as render smoke-tests — they pass if the component mounts without throwing.
