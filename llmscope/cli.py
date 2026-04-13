from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Literal, cast

import click
import httpx
import uvicorn

from llmscope.compare.engine import compare_models
from llmscope.export.csv_export import CsvExporter
from llmscope.export.json_export import JsonExporter
from llmscope.export.report import HtmlReportExporter
from llmscope.proxy.backends.llamacpp import LlamaCppBackend
from llmscope.proxy.backends.ollama import OllamaBackend
from llmscope.proxy.server import create_app
from llmscope.signals.drift import cosine_drift
from llmscope.signals.latency import compute_latency
from llmscope.store.db import DatabaseStore
from llmscope.types.config import AppConfig


@click.group()
def main() -> None:
    pass


@main.command()
@click.option(
    "--backend",
    default="ollama",
    type=click.Choice(["ollama", "llamacpp"]),
    show_default=True,
)
@click.option("--port", default=8080, type=int, show_default=True)
@click.option("--backend-url", default=None, type=str)
def start(backend: str, port: int, backend_url: str | None) -> None:
    logging.basicConfig(level=logging.INFO, format="[llmscope] %(message)s")

    backend_literal: Literal["ollama", "llamacpp"] = cast(
        Literal["ollama", "llamacpp"], backend
    )

    if backend_url is not None:
        config: AppConfig = AppConfig(
            backend=backend_literal,
            proxy_port=port,
            backend_url=backend_url,
        )
    else:
        config = AppConfig(backend=backend_literal, proxy_port=port)

    db: DatabaseStore = DatabaseStore(config.db_path)

    selected_backend: OllamaBackend | LlamaCppBackend = (
        OllamaBackend(config)
        if backend_literal == "ollama"
        else LlamaCppBackend(config)
    )

    app = create_app(config, db, selected_backend)

    click.echo(f"proxy  → http://0.0.0.0:{config.proxy_port}")
    click.echo(f"backend → {config.backend_url}")
    click.echo(f"db     → {config.db_path}")

    uvicorn.run(app, host="0.0.0.0", port=config.proxy_port, log_level="warning")


@main.command()
@click.option("--backend-url", default=None, type=str)
def init(backend_url: str | None) -> None:
    config: AppConfig = (
        AppConfig(backend_url=backend_url) if backend_url is not None else AppConfig()
    )

    db_path: str = os.path.expanduser(config.db_path)
    db_dir: str = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    click.echo(f"[ok] data directory : {db_dir}")

    store: DatabaseStore = DatabaseStore(config.db_path)
    version: int = store.get_schema_version()
    store.close()
    click.echo(f"[ok] database       : {db_path}  (schema v{version})")

    try:
        resp = httpx.get(f"{config.backend_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        click.echo(f"[ok] backend        : {config.backend_url}")
    except httpx.HTTPError:
        click.echo(
            f"[!] backend         : {config.backend_url}"
            " (unreachable — start it before running the proxy)"
        )

    click.echo("")
    click.echo("run:  llmscope start")


@main.command()
@click.option("--port", default=8080, type=int, show_default=True)
def status(port: int) -> None:
    url: str = f"http://localhost:{port}/api/stats"
    try:
        resp = httpx.get(url, timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        click.echo(f"proxy      : UP  (http://localhost:{port})")
        click.echo(f"total_runs : {data['total_runs']}")
        click.echo(f"total_tokens: {data['total_tokens']}")
        click.echo(f"avg_tps    : {data['avg_tps']}")
        click.echo(f"avg_ttft_ms: {data['avg_ttft_ms']}")
        if data["model_breakdown"]:
            click.echo("models:")
            for model, count in data["model_breakdown"].items():
                click.echo(f"  {model}: {count}")
    except httpx.HTTPError:
        click.echo(f"proxy      : DOWN  (http://localhost:{port})", err=True)
        raise SystemExit(1)


@main.group()
def db() -> None:
    pass


@db.command("stats")
@click.option("--db", "db_path", default="~/.llmscope/traces.db", show_default=True)
def db_stats(db_path: str) -> None:
    store: DatabaseStore = DatabaseStore(db_path)
    stats = store.get_stats()
    store.close()
    click.echo(f"total_runs  : {stats.total_runs}")
    click.echo(f"total_tokens: {stats.total_tokens}")
    click.echo(f"avg_tps     : {stats.avg_tps}")
    click.echo(f"avg_ttft_ms : {stats.avg_ttft_ms}")
    if stats.model_breakdown:
        click.echo("models:")
        for model, count in stats.model_breakdown.items():
            click.echo(f"  {model}: {count}")


@main.group()
def inspect() -> None:
    pass


@inspect.command("list")
@click.option("--db", default="~/.llmscope/traces.db", show_default=True)
@click.option("--limit", default=20, type=int, show_default=True)
def inspect_list(db: str, limit: int) -> None:
    store: DatabaseStore = DatabaseStore(db)
    runs = store.list_runs(limit=limit)
    store.close()
    if not runs:
        click.echo("no runs found")
        return
    cols = f"{'RUN ID':<10}  {'MODEL':<30}  {'BACKEND':<8}"
    header: str = f"{cols}  {'TPS':>7}  {'TOKENS':>7}  {'QUALITY':>8}"
    click.echo(header)
    click.echo("-" * len(header))
    for run in runs:
        tps_str: str = f"{run.tps:.2f}" if run.tps is not None else "?"
        tok_str: str = str(run.token_count) if run.token_count is not None else "?"
        qs_str = f"{run.quality_score:.3f}" if run.quality_score is not None else "?"
        click.echo(
            f"{run.run_id[:8]:<10}  {run.model:<30}  {run.backend:<8}  "
            f"{tps_str:>7}  {tok_str:>7}  {qs_str:>8}"
        )


@inspect.command("show")
@click.argument("run_id")
@click.option("--db", default="~/.llmscope/traces.db", show_default=True)
@click.option("--stall-threshold", default=500.0, type=float, show_default=True)
def inspect_show(run_id: str, db: str, stall_threshold: float) -> None:
    store: DatabaseStore = DatabaseStore(db)
    run = store.get_run(run_id)
    if run is None:
        click.echo(f"run not found: {run_id}", err=True)
        store.close()
        return
    tokens = store.get_tokens(run_id)
    output = store.get_output(run_id)
    store.close()

    click.echo(f"run_id     : {run.run_id}")
    click.echo(f"model      : {run.model}")
    click.echo(f"backend    : {run.backend}")
    click.echo(f"created_at : {run.created_at.isoformat()}")
    click.echo(f"ttft_ms    : {run.ttft_ms}")
    click.echo(f"total_ms   : {run.total_ms}")
    click.echo(f"tps        : {run.tps}")
    click.echo(f"token_count: {run.token_count}")
    click.echo(f"quality    : {run.quality_score}")
    click.echo(f"tags       : {run.tags}")

    if tokens:
        lat = compute_latency(
            arrived_ms=[t.arrived_at_ms for t in tokens],
            ttft_ms=run.ttft_ms or 0.0,
            total_ms=run.total_ms or 0.0,
            stall_threshold_ms=stall_threshold,
        )
        if lat.stall_positions:
            click.echo(f"stalls     : {lat.stall_positions}")

    if output is not None:
        click.echo("")
        click.echo(output.full_text)


@inspect.command("tail")
@click.option("--db", default="~/.llmscope/traces.db", show_default=True)
@click.option("--interval", default=2.0, type=float, show_default=True)
def inspect_tail(db: str, interval: float) -> None:
    store: DatabaseStore = DatabaseStore(db)
    seen: set[str] = {r.run_id for r in store.list_runs(limit=200)}
    click.echo(f"watching for new runs (interval={interval}s) — Ctrl-C to stop")
    try:
        while True:
            time.sleep(interval)
            for run in store.list_runs(limit=50):
                if run.run_id not in seen:
                    seen.add(run.run_id)
                    tps_str: str = f"{run.tps:.2f}" if run.tps is not None else "?"
                    qs_str: str = (
                        f"{run.quality_score:.3f}"
                        if run.quality_score is not None
                        else "?"
                    )
                    click.echo(
                        f"+ {run.run_id[:8]}  {run.model:<28}  "
                        f"tps={tps_str}  quality={qs_str}"
                    )
    except KeyboardInterrupt:
        pass
    finally:
        store.close()


@inspect.command("replay")
@click.argument("run_id")
@click.option("--db", default="~/.llmscope/traces.db", show_default=True)
@click.option(
    "--fast",
    is_flag=True,
    default=False,
    help="Print all tokens instantly without simulated timing.",
)
@click.option(
    "--max-gap",
    default=0.3,
    type=float,
    show_default=True,
    help="Cap per-token delay in seconds.",
)
def inspect_replay(run_id: str, db: str, fast: bool, max_gap: float) -> None:
    store: DatabaseStore = DatabaseStore(db)
    run = store.get_run(run_id)
    if run is None:
        click.echo(f"run not found: {run_id}", err=True)
        store.close()
        return
    tokens = store.get_tokens(run_id)
    store.close()

    click.echo(f"[{run.run_id[:8]}] {run.model} — replaying {len(tokens)} tokens")
    click.echo()

    for i, token in enumerate(tokens):
        if not fast and i > 0:
            gap: float = (
                token.arrived_at_ms - tokens[i - 1].arrived_at_ms
            ) / 1000.0
            time.sleep(min(gap, max_gap))
        click.echo(token.text, nl=False)

    click.echo()


@main.group()
def compare() -> None:
    pass


@compare.command("models")
@click.argument("prompt")
@click.option("--model", "models", multiple=True, required=True)
@click.option("--backend-url", default="http://localhost:11434", show_default=True)
def compare_models_cmd(
    prompt: str, models: tuple[str, ...], backend_url: str
) -> None:
    results = asyncio.run(
        compare_models(
            prompt=prompt,
            models=list(models),
            backend_url=backend_url,
        )
    )
    header: str = (
        f"{'MODEL':<30}  {'TTFT':>8}  {'TPS':>7}  {'TOKENS':>7}  {'QUALITY':>8}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for r in results:
        click.echo(
            f"{r.model:<30}  {r.ttft_ms:>8.1f}  {r.tps:>7.2f}  "
            f"{r.token_count:>7}  {r.quality.entropy_score:>8.4f}"
        )


@compare.command("drift")
@click.option("--run-a", required=True, type=str)
@click.option("--run-b", required=True, type=str)
@click.option("--db", default="~/.llmscope/traces.db", show_default=True)
def compare_drift(run_a: str, run_b: str, db: str) -> None:
    store: DatabaseStore = DatabaseStore(db)
    run_a_rec = store.get_run(run_a)
    run_b_rec = store.get_run(run_b)
    if run_a_rec is None:
        click.echo(f"run not found: {run_a}", err=True)
        store.close()
        return
    if run_b_rec is None:
        click.echo(f"run not found: {run_b}", err=True)
        store.close()
        return
    tokens_a = [t.text for t in store.get_tokens(run_a)]
    tokens_b = [t.text for t in store.get_tokens(run_b)]
    store.close()

    result = cosine_drift(run_a, tokens_a, run_b, tokens_b)

    click.echo(f"run A      : {result.run_a_id[:8]}  ({run_a_rec.model})")
    click.echo(f"run B      : {result.run_b_id[:8]}  ({run_b_rec.model})")
    click.echo(f"drift      : {result.cosine_drift:.4f}")
    click.echo(
        f"significant: {'yes ⚠' if result.is_significant else 'no'}"
    )


@main.group()
def config() -> None:
    pass


@config.command("show")
@click.option("--backend", default=None, type=click.Choice(["ollama", "llamacpp"]))
@click.option("--port", default=None, type=int)
@click.option("--backend-url", default=None, type=str)
def config_show(
    backend: str | None,
    port: int | None,
    backend_url: str | None,
) -> None:
    backend_literal: Literal["ollama", "llamacpp"] = cast(
        Literal["ollama", "llamacpp"], backend or "ollama"
    )
    kwargs: dict[str, object] = {"backend": backend_literal}
    if port is not None:
        kwargs["proxy_port"] = port
    if backend_url is not None:
        kwargs["backend_url"] = backend_url

    cfg: AppConfig
    if port is not None and backend_url is not None:
        cfg = AppConfig(
            backend=backend_literal, proxy_port=port, backend_url=backend_url
        )
    elif port is not None:
        cfg = AppConfig(backend=backend_literal, proxy_port=port)
    elif backend_url is not None:
        cfg = AppConfig(backend=backend_literal, backend_url=backend_url)
    else:
        cfg = AppConfig(backend=backend_literal)

    click.echo(f"backend          : {cfg.backend}")
    click.echo(f"proxy_port       : {cfg.proxy_port}")
    click.echo(f"backend_url      : {cfg.backend_url}")
    click.echo(f"db_path          : {cfg.db_path}")
    click.echo(f"queue_maxsize    : {cfg.queue_maxsize}")
    click.echo(f"stall_threshold  : {cfg.stall_threshold_ms} ms")
    click.echo(f"dashboard_port   : {cfg.dashboard_port}")
    click.echo("")
    click.echo("env overrides: LLMSCOPE_BACKEND, LLMSCOPE_PROXY_PORT,")
    click.echo("               LLMSCOPE_BACKEND_URL, LLMSCOPE_DB_PATH")


@main.command()
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "csv", "html"]),
    show_default=True,
)
@click.option("--output", "output_path", required=True, type=str)
@click.option("--db", default="~/.llmscope/traces.db", show_default=True)
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--title", default="Run Report", type=str, show_default=True)
def export(
    fmt: str,
    output_path: str,
    db: str,
    limit: int,
    title: str,
) -> None:
    store: DatabaseStore = DatabaseStore(db)
    runs = store.list_runs(limit=limit)
    store.close()

    if fmt == "json":
        asyncio.run(JsonExporter().export(runs, output_path))
    elif fmt == "csv":
        asyncio.run(CsvExporter().export(runs, output_path))
    elif fmt == "html":
        asyncio.run(HtmlReportExporter().export(runs, output_path, title=title))

    click.echo(f"exported {len(runs)} run(s) → {output_path}")
