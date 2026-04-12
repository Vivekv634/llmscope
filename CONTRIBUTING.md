# Contributing to LLMScope

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- Node.js 20+ and npm (dashboard work only)
- Ollama or llama.cpp running locally

## Setup

```bash
git clone https://github.com/Vivekv634/llmscope
cd llmscope
poetry install
```

## Development modes

### A — Backend only

No Node.js required. Use this when working purely on the Python proxy, CLI, signals, or store.

```bash
poetry run llmscope start
```

API is available at `http://localhost:8080`. The dashboard will not be served unless you have previously run the build script (see mode C).

### B — Full stack with hot reload

Use this when actively working on dashboard code.

Terminal 1:
```bash
poetry run llmscope start
```

Terminal 2:
```bash
cd dashboard
npm install
npm run dev
```

Dashboard runs at `http://localhost:3000` with hot reload. It talks to the proxy at `http://localhost:8080`.

### C — Production-like (static export)

Use this to verify the packaged dashboard before cutting a release.

```bash
bash scripts/build_dashboard.sh
poetry run llmscope start
```

Both API and dashboard are served on `http://localhost:8080`, the same as a `pip install` user would experience.

## Before opening a pull request

```bash
poetry run pytest                   # all tests must pass
poetry run mypy llmscope/ --strict  # no type errors
poetry run ruff check llmscope/     # no lint issues
```

If you changed dashboard code:

```bash
cd dashboard && npm run build       # TypeScript and build must be clean
```

## Project layout

```
llmscope/           Python package
  proxy/            FastAPI app, backends, interceptor
  store/            DuckDB store and queries
  signals/          Latency, quality, drift computations
  compare/          Multi-model comparison engine
  export/           JSON, CSV, HTML exporters
  types/            Pydantic models shared across modules
  cli.py            Click CLI entry point
  static/           Pre-built dashboard (generated, not committed)

dashboard/          Next.js 15 source
  app/              App Router pages
  components/       React components
  lib/api.ts        Typed REST client
  types/api.ts      Shared TypeScript types

scripts/
  build_dashboard.sh  Builds Next.js → copies to llmscope/static/

tests/              Mirrors llmscope/ package structure
```

## Key rules

- Every new module must have a corresponding test file.
- No inline comments, block comments, or docstrings — code should be self-evident.
- Full type annotations required; `mypy --strict` must pass.
- Next.js is the only frontend framework — no alternatives.
- `llmscope/static/` and `dashboard/out/` are build artifacts — do not commit them.
