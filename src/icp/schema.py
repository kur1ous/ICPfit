"""The output contract.

These Pydantic models are handed to Gemini as a response schema, so the model
is forced to return machine-consumable fields rather than prose we regex later.
Crucially, `icp_fit_reasoning` is required and non-empty: the score is never
allowed to stand alone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EmployeeBucket(str, Enum):
    XS = "1-10"
    S = "11-50"
    M = "51-200"
    L = "201-500"
    XL = "501-1000"
    XXL = "1000+"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EnrichmentResult(BaseModel):
    """Model-generated judgment about an account. This is the LLM's response schema."""

    company_name: str = Field(description="Official company name.")
    what_it_does: str = Field(
        description="One or two sentences on what the company does."
    )
    industry: str = Field(description="Primary industry / vertical.")
    employee_count_estimate: EmployeeBucket = Field(
        description="Rough headcount bucket inferred from signals. Use 'unknown' if no basis."
    )
    icp_fit_score: int = Field(
        ge=1, le=5, description="ICP fit, 1 (poor) to 5 (excellent), scored against the ICP definition."
    )
    icp_fit_reasoning: str = Field(
        min_length=1,
        description="Why this score, citing concrete signals. REQUIRED — never return a bare score.",
    )
    buyer_persona: str = Field(
        description="The likely buyer/decision-maker persona (role/title)."
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="Pain points inferable from the signals that our product could address.",
    )
    confidence: Confidence = Field(
        description="How confident the model is in this judgment given the available signals."
    )


class EnrichmentRecord(BaseModel):
    """What we persist: the model result plus pipeline metadata (not model-generated)."""

    domain: str
    result: EnrichmentResult
    model: str
    prompt_version: str
    signals_used: list[str]
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def flat(self) -> dict:
        """Flattened dict for CSV export."""
        r = self.result
        return {
            "domain": self.domain,
            "company_name": r.company_name,
            "what_it_does": r.what_it_does,
            "industry": r.industry,
            "employee_count_estimate": r.employee_count_estimate.value,
            "icp_fit_score": r.icp_fit_score,
            "icp_fit_reasoning": r.icp_fit_reasoning,
            "buyer_persona": r.buyer_persona,
            "pain_points": "; ".join(r.pain_points),
            "confidence": r.confidence.value,
            "signals_used": ",".join(self.signals_used),
            "model": self.model,
            "prompt_version": self.prompt_version,
            "created_at": self.created_at,
        }
