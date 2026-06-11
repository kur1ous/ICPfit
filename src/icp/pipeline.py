"""Orchestration: domain -> cached-or-fetched signals -> enrich -> store.

`enrich_domain` is idempotent and cache-aware. `batch` runs many domains with
bounded concurrency.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import cache, config
from .enrich import enrich
from .fetch import fetch_signals, normalize_domain
from .schema import EnrichmentRecord

log = logging.getLogger("icp")


def enrich_domain(
    domain: str,
    *,
    force: bool = False,
    db_path: Path | None = None,
) -> EnrichmentRecord:
    """Enrich a single domain. Returns a cached result unless force=True."""
    domain = normalize_domain(domain)

    if not force:
        cached = cache.get_result(domain, config.PROMPT_VERSION, config.MODEL, db_path)
        if cached:
            log.info("[%s] result cache HIT", domain)
            return cached

    signals = None if force else cache.get_signals(domain, db_path)
    if signals is None:
        log.info("[%s] fetching signals", domain)
        signals = fetch_signals(domain)
        cache.set_signals(domain, signals, db_path)
    else:
        log.info("[%s] signals cache HIT", domain)

    log.info("[%s] calling %s", domain, config.MODEL)
    result = enrich(domain, signals)

    record = EnrichmentRecord(
        domain=domain,
        result=result,
        model=config.MODEL,
        prompt_version=config.PROMPT_VERSION,
        signals_used=list(signals.keys()),
    )
    cache.set_result(record, db_path)
    return record


def batch(
    domains: list[str],
    *,
    force: bool = False,
    concurrency: int = 4,
    db_path: Path | None = None,
) -> list[EnrichmentRecord]:
    """Enrich many domains with bounded concurrency. Skips ones that error
    (logged) so one bad domain doesn't sink the run."""
    results: list[EnrichmentRecord] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(enrich_domain, d, force=force, db_path=db_path): d
            for d in domains
        }
        for fut in as_completed(futures):
            d = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                log.error("[%s] FAILED: %s", normalize_domain(d), exc)
    return results
