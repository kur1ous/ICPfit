"""SQLite cache + results store — so we never pay for the same domain twice.

Two tables, deliberately separated:
  - signals: raw fetched page text, keyed by domain. Changing the prompt does
    NOT force a re-fetch.
  - results: enrichment output, keyed by (domain, prompt_version, model). Bump
    PROMPT_VERSION to re-run cleanly without wiping anything.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .schema import EnrichmentRecord, EnrichmentResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    domain      TEXT PRIMARY KEY,
    signals_json TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    domain         TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model          TEXT NOT NULL,
    result_json    TEXT NOT NULL,
    signals_used   TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (domain, prompt_version, model)
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or config.DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


# --- signals ----------------------------------------------------------------

def get_signals(domain: str, db_path: Path | None = None) -> dict[str, str] | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT signals_json FROM signals WHERE domain = ?", (domain,)
        ).fetchone()
    return json.loads(row["signals_json"]) if row else None


def set_signals(domain: str, signals: dict[str, str], db_path: Path | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO signals (domain, signals_json, fetched_at) VALUES (?, ?, ?)",
            (domain, json.dumps(signals), datetime.now(timezone.utc).isoformat()),
        )


# --- results ----------------------------------------------------------------

def get_result(
    domain: str,
    prompt_version: str,
    model: str,
    db_path: Path | None = None,
) -> EnrichmentRecord | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM results WHERE domain = ? AND prompt_version = ? AND model = ?",
            (domain, prompt_version, model),
        ).fetchone()
    if not row:
        return None
    return EnrichmentRecord(
        domain=row["domain"],
        result=EnrichmentResult.model_validate_json(row["result_json"]),
        model=row["model"],
        prompt_version=row["prompt_version"],
        signals_used=row["signals_used"].split(",") if row["signals_used"] else [],
        created_at=row["created_at"],
    )


def set_result(record: EnrichmentRecord, db_path: Path | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO results
               (domain, prompt_version, model, result_json, signals_used, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                record.domain,
                record.prompt_version,
                record.model,
                record.result.model_dump_json(),
                ",".join(record.signals_used),
                record.created_at,
            ),
        )
