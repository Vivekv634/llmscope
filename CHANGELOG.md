# Changelog

## [0.1.0] - 2026-04-12

### Added

**Core proxy**
- Transparent HTTP proxy for Ollama and llama.cpp with asyncio queue worker
- Token-level event stream: `RunStartEvent`, `TTFTEvent`, `TokenEvent`, `DoneEvent`
- WebSocket endpoint `/ws/stream/{run_id}` for live token feed
- CORS middleware allowing `http://localhost:3000`

**Storage**
- DuckDB-backed `DatabaseStore` with schema auto-apply on init
- Tables: `runs`, `tokens`, `outputs`
- `finalize_run` computes TPS, token count, and Shannon entropy quality score
- Tag support: `set_tags`, persisted as JSON in the `runs` table

**Signals**
- `compute_latency` — TTFT, total ms, TPS, stall position detection
- `output_entropy` — Shannon entropy of token distribution, normalised 0–1
- `cosine_drift` — cosine similarity between two token sequences via TF vectors

**REST API**
- `GET /api/runs` — paginated run list
- `GET /api/runs/{id}` — single run record
- `GET /api/runs/{id}/tokens` — token records
- `GET /api/runs/{id}/output` — full output text
- `GET /api/runs/{id}/signals` — latency + quality signals
- `GET /api/runs/{id}/drift?compare_to={id}` — cosine drift vs another run
- `PUT /api/runs/{id}/tags` — replace tag set
- `GET /api/models` — model list from backend
- `GET /api/stats` — aggregate counts, averages, model breakdown
- `POST /api/compare` — parallel multi-model comparison
- `POST /api/generate` and `POST /api/chat` — proxied streaming endpoints

**CLI**
- `llmscope start` — launch proxy with backend selection and port config
- `llmscope status` — health check with live DB stats
- `llmscope db stats` — offline aggregate stats from DuckDB file
- `llmscope inspect list/show/tail/replay` — run browsing and replay
- `llmscope compare models/drift` — multi-model and drift analysis
- `llmscope export` — JSON, CSV, HTML export via anyio
- `llmscope config show` — resolved configuration

**Dashboard** (Next.js 15 App Router)
- Home page with `RunsFilter` — client-side model pill filter
- Run detail page with `LatencyTimeline`, `QualityScore`, `TagEditor`, `LiveFeed`
- Live token feed over WebSocket with blinking cursor while streaming
- Compare page (`/runs/compare?a=&b=`) — side-by-side run diff with drift badge
- Multi-model compare page with `ModelToggle` and tabular results
- Typed REST client in `lib/api.ts` with absolute `http://localhost:8080` base

**Backends**
- `OllamaBackend` — Ollama generate + chat endpoints
- `LlamaCppBackend` — llama.cpp generate + chat endpoints
- `AbstractBackend` Protocol for extensibility

**Packaging**
- Dashboard compiled to a static export (`next build`, `output: "export"`) and bundled inside the Python wheel under `llmscope/static/`
- `llmscope start` serves both API and dashboard on a single port — no Node.js required by end users
- `scripts/build_dashboard.sh` — builds Next.js and copies output to `llmscope/static/`
- `llmscope/static/` and `dashboard/out/` excluded from git; generated fresh in CI before `poetry build`
- All Next.js pages converted to client components; dynamic `/runs/[id]` route replaced with query-param `/runs?id=` for static export compatibility

**CI/CD**
- GitHub Actions: lint → typecheck → test (sequential fail-fast)
- PyPI publish workflow builds the dashboard (`scripts/build_dashboard.sh`) before `poetry build`, so every release wheel contains the latest UI
- `actions/setup-node@v4` added to the publish workflow

**Docs**
- `README.md` — three development modes (backend only, full stack hot reload, production-like static)
- `CONTRIBUTING.md` — full contributor guide covering setup, dev modes, pre-PR checks, project layout, and key rules
- `CHANGELOG.md` — this file

[0.1.0]: https://github.com/Vivekv634/llmscope/releases/tag/v0.1.0
