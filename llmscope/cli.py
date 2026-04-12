from __future__ import annotations

import asyncio
import logging
from typing import Literal, Optional, cast

import click
import uvicorn

from llmscope.compare.engine import compare_models
from llmscope.export.csv_export import CsvExporter
from llmscope.export.json_export import JsonExporter
from llmscope.export.report import HtmlReportExporter
from llmscope.proxy.backends.llamacpp import LlamaCppBackend
from llmscope.proxy.backends.ollama import OllamaBackend
from llmscope.proxy.server import create_app
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
def start(backend: str, port: int, backend_url: Optional[str]) -> None:
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


@main.group()
def inspect() -> None:
    pass


@inspect.command("list")
@click.option(
    "--db",
    default="~/.llmscope/traces.db",
    show_default=True,
    help="Path to the DuckDB traces file.",
)
@click.option("--limit", default=20, type=int, show_default=True)
def inspect_list(db: str, limit: int) -> None:
    store: DatabaseStore = DatabaseStore(db)
    runs = store.list_runs(limit=limit)
    store.close()
    if not runs:
        click.echo("no runs found")
        return
    header: str = f"{'RUN ID':<10}  {'MODEL':<30}  {'BACKEND':<8}  {'TPS':>7}  {'TOKENS':>7}"
    click.echo(header)
    click.echo("-" * len(header))
    for run in runs:
        tps_str: str = f"{run.tps:.2f}" if run.tps is not None else "?"
        tok_str: str = str(run.token_count) if run.token_count is not None else "?"
        click.echo(
            f"{run.run_id[:8]:<10}  {run.model:<30}  {run.backend:<8}  {tps_str:>7}  {tok_str:>7}"
        )


@inspect.command("show")
@click.argument("run_id")
@click.option(
    "--db",
    default="~/.llmscope/traces.db",
    show_default=True,
    help="Path to the DuckDB traces file.",
)
@click.option(
    "--stall-threshold",
    default=500.0,
    type=float,
    show_default=True,
    help="Gap in ms above which a token gap is considered a stall.",
)
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


@main.command()
@click.argument("prompt")
@click.option(
    "--model",
    "models",
    multiple=True,
    required=True,
    help="Model name (repeat for multiple).",
)
@click.option(
    "--backend-url",
    default="http://localhost:11434",
    show_default=True,
)
def compare(prompt: str, models: tuple[str, ...], backend_url: str) -> None:
    results = asyncio.run(
        compare_models(
            prompt=prompt,
            models=list(models),
            backend_url=backend_url,
        )
    )
    header: str = f"{'MODEL':<30}  {'TTFT':>8}  {'TPS':>7}  {'TOKENS':>7}  {'QUALITY':>8}"
    click.echo(header)
    click.echo("-" * len(header))
    for r in results:
        click.echo(
            f"{r.model:<30}  {r.ttft_ms:>8.1f}  {r.tps:>7.2f}  {r.token_count:>7}  {r.quality.entropy_score:>8.4f}"
        )


@main.command()
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "csv", "html"]),
    show_default=True,
)
@click.option("--output", "output_path", required=True, type=str)
@click.option(
    "--db",
    default="~/.llmscope/traces.db",
    show_default=True,
)
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
