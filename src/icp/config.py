"""Pipeline configuration.

The single most important knob here is ICP_DEFINITION. A fit score is only
meaningful relative to a clear definition of who your ideal customer is.
Replace the placeholder below with your real target profile before trusting
any scores.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- LLM ---------------------------------------------------------------------
# Cheap/fast first-pass model. Free tier on Google AI Studio.
MODEL = "gemini-2.5-flash"

# Bump this when you change the prompt or schema in a way that should
# invalidate cached results. Old results stay in the DB under their old
# version, so this is safe and reversible.
PROMPT_VERSION = "v1"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- ICP definition (EDIT ME) ------------------------------------------------
# TODO: Replace this entire string with your actual ideal customer profile.
# Be concrete: target industries, company size, the signals that indicate a
# good fit, and the disqualifiers. The model scores 1-5 against THIS text.
ICP_DEFINITION = """\
TODO — replace with your real ICP. Example placeholder:

We sell a developer-focused API observability product.

Strong fit (5):
- B2B SaaS companies that ship software as their core product
- 50-1000 employees
- Public signals of an engineering org (careers page with backend/platform
  roles, a developer docs or API section, usage-based pricing)

Weak fit (1-2):
- Agencies, consultancies, or services businesses
- Non-technical companies (retail, hospitality) with no engineering org
- Sub-10-person companies with no clear product

Disqualifiers: direct competitors, companies with no website content.
"""

# --- Fetch -------------------------------------------------------------------
# Paths probed on each domain. Add new signal sources here.
FETCH_PATHS = ["/", "/about", "/pricing", "/careers"]
FETCH_TIMEOUT_SECONDS = 10.0
USER_AGENT = (
    "Mozilla/5.0 (compatible; ICP-Enrichment/0.1; "
    "+https://github.com/) Python-httpx"
)
# Per-source char budget handed to the LLM (keeps token cost bounded).
MAX_CHARS_PER_SOURCE = 6000

# --- Storage -----------------------------------------------------------------
DB_PATH = Path(os.environ.get("ICP_DB_PATH", "icp.db"))
