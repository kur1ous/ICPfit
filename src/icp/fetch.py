"""Signal gathering: turn a domain into a dict of {source: extracted_text}.

We probe a fixed set of paths, extract the readable main text with trafilatura
(falling back to a crude HTML strip), and skip anything that 404s or comes back
empty. Failures are non-fatal — partial signals still produce a usable judgment.
"""

from __future__ import annotations

import re

import httpx
import trafilatura
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from . import config

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def normalize_domain(domain: str) -> str:
    """Strip scheme/path/www and lowercase. 'https://www.Foo.com/x' -> 'foo.com'."""
    d = domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    reraise=False,
)
def _get(client: httpx.Client, url: str) -> httpx.Response | None:
    resp = client.get(url)
    return resp


def _extract(html: str) -> str:
    extracted = trafilatura.extract(html) or ""
    if not extracted.strip():
        extracted = _strip_html(html)
    return extracted.strip()[: config.MAX_CHARS_PER_SOURCE]


def fetch_signals(domain: str) -> dict[str, str]:
    """Fetch configured paths for a domain. Returns {source_path: text} for pages
    that returned 2xx with non-empty extracted text."""
    domain = normalize_domain(domain)
    base = f"https://{domain}"
    signals: dict[str, str] = {}

    headers = {"User-Agent": config.USER_AGENT}
    with httpx.Client(
        headers=headers,
        timeout=config.FETCH_TIMEOUT_SECONDS,
        follow_redirects=True,
    ) as client:
        for path in config.FETCH_PATHS:
            url = base.rstrip("/") + path
            try:
                resp = _get(client, url)
            except Exception:
                resp = None
            if resp is None or resp.status_code >= 400:
                continue
            text = _extract(resp.text)
            if text:
                signals[path] = text

    return signals
