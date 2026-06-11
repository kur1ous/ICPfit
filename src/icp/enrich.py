"""The LLM call: signals -> structured EnrichmentResult.

Uses Gemini structured-output mode with the Pydantic schema, so the response
parses straight into our contract — no free-text parsing, no regex.
"""

from __future__ import annotations

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from . import config
from .schema import EnrichmentResult

_SYSTEM = """\
You are an ICP-fit analyst. You are given text scraped from a company's public
website (homepage, about, pricing, careers). Judge how well the company matches
the ideal customer profile below, and return ONLY the structured fields.

Rules:
- Base every field on evidence in the provided text. Do not invent facts.
- If a signal is missing, reflect that with 'unknown' / lower confidence rather
  than guessing confidently.
- icp_fit_reasoning must cite the concrete signals behind the score. Never
  return a score without justifying it.

=== IDEAL CUSTOMER PROFILE ===
{icp}
=== END ICP ===
"""


def _client() -> genai.Client:
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _build_user_prompt(domain: str, signals: dict[str, str]) -> str:
    parts = [f"Company domain: {domain}", ""]
    if not signals:
        parts.append("(No page text could be fetched. Judge conservatively.)")
    for source, text in signals.items():
        parts.append(f"--- SOURCE: {source} ---")
        parts.append(text)
        parts.append("")
    return "\n".join(parts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10), reraise=True)
def enrich(domain: str, signals: dict[str, str]) -> EnrichmentResult:
    """Call Gemini and return a validated EnrichmentResult."""
    client = _client()
    system = _SYSTEM.format(icp=config.ICP_DEFINITION)
    user = _build_user_prompt(domain, signals)

    resp = client.models.generate_content(
        model=config.MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=EnrichmentResult,
            temperature=0.2,
        ),
    )

    parsed = resp.parsed
    if isinstance(parsed, EnrichmentResult):
        return parsed
    # Fallback: validate from raw text if the SDK didn't auto-parse.
    if not resp.text:
        raise RuntimeError(f"Empty response from model for {domain}")
    return EnrichmentResult.model_validate_json(resp.text)
