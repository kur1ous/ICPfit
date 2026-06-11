# ICP-Fit Enrichment Pipeline

Given a company **domain**, fetch its public signals (homepage, /about, /pricing,
/careers), hand the text to an LLM under a fixed JSON schema, and get back
structured judgment: what the company does, industry, rough headcount, an
**ICP-fit score (1–5) with reasoning**, the likely buyer persona, and inferred
pain points. Results land in a local SQLite DB that doubles as a per-domain cache.

## Design principles (baked in)

1. **Structured output** — Gemini structured-output mode with a Pydantic
   `response_schema` (`src/icp/schema.py`). No regex over prose.
2. **A reason beside every score** — `icp_fit_reasoning` is a required,
   non-empty field. No bare "4/5".
3. **A tiny eval set** — `eval/labels.csv` + `eval/run_eval.py` measure agreement
   with your own hand labels. Run it before you scale.
4. **Cache by domain** — SQLite (`src/icp/cache.py`); never pay twice. Cheap, fast
   model (Gemini 2.5 Flash, free tier) on the first pass.

## Setup

```bash
pip install -e .
cp .env.example .env        # then add your GEMINI_API_KEY
```

Get a free key at https://aistudio.google.com/apikey.

**Then edit `src/icp/config.py` → `ICP_DEFINITION`.** A fit score is meaningless
until this describes *your* ideal customer. This is the most important step.

## Usage

```bash
icp enrich stripe.com               # single domain, pretty output
icp enrich stripe.com --json        # raw JSON
icp enrich stripe.com --force       # ignore cache, re-run

icp batch eval/labels.csv --out results.csv --concurrency 4
```

## Evaluate before scaling

1. Hand-label 20–30 companies in `eval/labels.csv` (column `human_score`, 1–5)
   — score them yourself *before* looking at model output.
2. `python eval/run_eval.py` → agreement %, within-±1, MAE, a 5×5 confusion
   matrix, and a dump of every disagreement *with the model's reasoning*.

If agreement is poor, tighten `ICP_DEFINITION` (and bump `PROMPT_VERSION` to
re-run cleanly), then re-evaluate.

## Tests

```bash
pytest          # schema enforcement, cache round-trips, fetch extraction (offline)
```

## What's next

This is step 1. Each later step consumes the previous one's output:
enrichment → lead scoring/routing → signal monitoring → personalization. Clean
seams already exist for model-tier escalation (`config.py` + `confidence` field)
and a CRM/warehouse writer (reads the `results` table).
