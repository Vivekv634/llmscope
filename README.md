# LLMScope

Local LLM inference observatory for [Ollama](https://ollama.com) and [llama.cpp](https://llama-cpp.com/). Records every inference call with timing signals, stores results in a local DuckDB database, and visualises them in a Next.js dashboard.

## Features

- **Transparent proxy** — drop it in front of any Ollama or llama.cpp server with no client-side changes
- **Token-level timing** — TTFT, per-token gaps, stall detection
- **Quality scoring** — Shannon entropy of the token distribution per run
- **Drift detection** — cosine similarity between two runs to detect model regressions
- **Multi-model comparison** — run the same prompt against multiple models in parallel
- **Tag runs** — annotate runs for filtering and reporting
- **Live dashboard** — Next.js 15 App Router UI with WebSocket token feed
- **Export** — JSON, CSV, or HTML report

## Install

```bash
pip install llmscope
```

Requires Python 3.11+.

## Quick start

```bash
llmscope start                          # proxy on :8080, backend at :11434
llmscope start --port 8081 --backend llamacpp --backend-url http://localhost:8000
```

Point your LLM client at `http://localhost:8080` instead of the backend directly.

## Dashboard

The dashboard is a separate Next.js 15 app located in the `dashboard/` directory.

```bash
cd dashboard
npm install
npm run dev       # http://localhost:3000
```

The proxy must be running on port 8080 for the dashboard to fetch data.

## CLI reference

### `llmscope start`

Start the proxy server.

```
Options:
  --backend [ollama|llamacpp]   Backend type  [default: ollama]
  --port INTEGER                Proxy listen port  [default: 8080]
  --backend-url TEXT            Override backend base URL
```

### `llmscope status`

Check whether the proxy is reachable and print aggregate DB stats.

```bash
llmscope status
llmscope status --port 8081
```

### `llmscope db stats`

Print aggregate statistics from the local database without requiring the proxy to be running.

```bash
llmscope db stats
llmscope db stats --db ~/custom/path.db
```

### `llmscope inspect list`

List recent runs.

```bash
llmscope inspect list --limit 10
```

### `llmscope inspect show <run_id>`

Show full details for a single run including output text and stall positions.

```bash
llmscope inspect show abc12345
```

### `llmscope inspect tail`

Watch for new runs in real time.

```bash
llmscope inspect tail --interval 1.0
```

### `llmscope inspect replay <run_id>`

Replay recorded token stream with original timing.

```bash
llmscope inspect replay abc12345
llmscope inspect replay abc12345 --fast
```

### `llmscope compare models`

Run the same prompt against multiple models and compare results.

```bash
llmscope compare models "explain recursion" \
  --model llama3.2 \
  --model mistral:7b
```

### `llmscope compare drift`

Compute cosine drift between two runs.

```bash
llmscope compare drift --run-a abc12345 --run-b def67890
```

### `llmscope export`

Export runs to JSON, CSV, or HTML.

```bash
llmscope export --format json --output runs.json
llmscope export --format csv  --output runs.csv  --limit 500
llmscope export --format html --output report.html --title "Weekly Report"
```

### `llmscope config show`

Print the resolved configuration (with any env var overrides applied).

## Environment variables

| Variable               | Default                  | Description       |
| ---------------------- | ------------------------ | ----------------- |
| `LLMSCOPE_BACKEND`     | `ollama`                 | Backend type      |
| `LLMSCOPE_PROXY_PORT`  | `8080`                   | Proxy listen port |
| `LLMSCOPE_BACKEND_URL` | `http://localhost:11434` | Backend base URL  |
| `LLMSCOPE_DB_PATH`     | `~/.llmscope/traces.db`  | DuckDB file path  |

## REST API

The proxy exposes a REST API at the same port.

| Method | Path                                   | Description                    |
| ------ | -------------------------------------- | ------------------------------ |
| `GET`  | `/api/runs`                            | List runs (optional `?limit=`) |
| `GET`  | `/api/runs/{id}`                       | Get single run                 |
| `GET`  | `/api/runs/{id}/tokens`                | Token records for a run        |
| `GET`  | `/api/runs/{id}/output`                | Full output text               |
| `GET`  | `/api/runs/{id}/signals`               | Latency + quality signals      |
| `GET`  | `/api/runs/{id}/drift?compare_to={id}` | Cosine drift vs another run    |
| `PUT`  | `/api/runs/{id}/tags`                  | Set tags `{"tags": [...]}`     |
| `GET`  | `/api/models`                          | List models from backend       |
| `GET`  | `/api/stats`                           | Aggregate DB statistics        |
| `POST` | `/api/compare`                         | Multi-model comparison         |
| `POST` | `/api/generate`                        | Proxied generate endpoint      |
| `POST` | `/api/chat`                            | Proxied chat endpoint          |
| `WS`   | `/ws/stream/{id}`                      | Live token stream              |

## Development

### Prerequisites

- Python 3.11+, [Poetry](https://python-poetry.org/docs/#installation)
- Node.js 20+ and npm (dashboard work only)
- Ollama or llama.cpp running locally

### Setup

```bash
git clone https://github.com/Vivekv634/llmscope
cd llmscope
poetry install
```

### Development modes

**Backend only** — proxy, CLI, signals, store. No Node.js needed.

```bash
poetry run llmscope start
```

**Full stack with hot reload** — use when working on dashboard code.

```bash
# terminal 1
poetry run llmscope start

# terminal 2
cd dashboard && npm install && npm run dev   # http://localhost:3000
```

**Production-like** — verifies the static export end-to-end before a release.

```bash
bash scripts/build_dashboard.sh   # builds Next.js → llmscope/static/
poetry run llmscope start         # serves API + dashboard on :8080
```

### Checks

```bash
poetry run pytest
poetry run mypy llmscope/ --strict
poetry run ruff check llmscope/
cd dashboard && npm run build     # if dashboard code changed
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributor guide.

## License

MIT
