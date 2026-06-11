"""Command-line entrypoint.

  icp enrich <domain> [--force] [--json]
  icp batch <domains.csv> [--out results.csv] [--concurrency N] [--force]
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

import typer

from . import pipeline
from .schema import EnrichmentRecord

app = typer.Typer(add_completion=False, help="ICP-fit enrichment pipeline.")


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _print_human(rec: EnrichmentRecord) -> None:
    r = rec.result
    bar = "*" * r.icp_fit_score + "-" * (5 - r.icp_fit_score)
    typer.echo("")
    typer.secho(f"{r.company_name}  ({rec.domain})", bold=True)
    typer.echo(f"  ICP fit:    {bar}  {r.icp_fit_score}/5   [confidence: {r.confidence.value}]")
    typer.echo(f"  Industry:   {r.industry}")
    typer.echo(f"  Headcount:  {r.employee_count_estimate.value}")
    typer.echo(f"  Does:       {r.what_it_does}")
    typer.echo(f"  Buyer:      {r.buyer_persona}")
    typer.echo(f"  Pain:       {'; '.join(r.pain_points) or '—'}")
    typer.echo(f"  Reasoning:  {r.icp_fit_reasoning}")
    typer.echo(f"  Signals:    {', '.join(rec.signals_used) or '(none fetched)'}")
    typer.echo("")


@app.command()
def enrich(
    domain: str,
    force: bool = typer.Option(False, "--force", help="Ignore cache and re-run."),
    as_json: bool = typer.Option(False, "--json", help="Print raw JSON."),
) -> None:
    """Enrich a single domain."""
    _setup_logging()
    rec = pipeline.enrich_domain(domain, force=force)
    if as_json:
        typer.echo(json.dumps(rec.model_dump(mode="json"), indent=2))
    else:
        _print_human(rec)


@app.command()
def batch(
    csv_path: Path = typer.Argument(..., help="CSV with a 'domain' column."),
    out: Path = typer.Option(None, "--out", help="Write flattened results CSV here."),
    concurrency: int = typer.Option(4, "--concurrency"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Enrich every domain in a CSV (column 'domain')."""
    _setup_logging()
    with open(csv_path, newline="", encoding="utf-8") as f:
        domains = [row["domain"].strip() for row in csv.DictReader(f) if row.get("domain", "").strip()]

    typer.echo(f"Enriching {len(domains)} domains (concurrency={concurrency})...")
    records = pipeline.batch(domains, force=force, concurrency=concurrency)

    if out:
        rows = [r.flat() for r in records]
        if rows:
            with open(out, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        typer.echo(f"Wrote {len(rows)} rows to {out}")
    typer.echo(f"Done: {len(records)}/{len(domains)} enriched.")


if __name__ == "__main__":
    app()
