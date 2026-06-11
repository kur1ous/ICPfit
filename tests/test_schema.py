import pytest
from pydantic import ValidationError

from icp.schema import Confidence, EmployeeBucket, EnrichmentRecord, EnrichmentResult


def _valid(**overrides):
    base = dict(
        company_name="Acme",
        what_it_does="Sells widgets.",
        industry="Manufacturing",
        employee_count_estimate=EmployeeBucket.M,
        icp_fit_score=4,
        icp_fit_reasoning="Mid-size B2B with engineering roles.",
        buyer_persona="VP Engineering",
        pain_points=["scaling"],
        confidence=Confidence.HIGH,
    )
    base.update(overrides)
    return EnrichmentResult(**base)


def test_valid_result():
    r = _valid()
    assert r.icp_fit_score == 4


@pytest.mark.parametrize("bad", [0, 6, -1, 10])
def test_score_out_of_range_rejected(bad):
    with pytest.raises(ValidationError):
        _valid(icp_fit_score=bad)


def test_empty_reasoning_rejected():
    with pytest.raises(ValidationError):
        _valid(icp_fit_reasoning="")


def test_flatten_record():
    rec = EnrichmentRecord(
        domain="acme.com",
        result=_valid(),
        model="gemini-2.5-flash",
        prompt_version="v1",
        signals_used=["/", "/about"],
    )
    flat = rec.flat()
    assert flat["domain"] == "acme.com"
    assert flat["icp_fit_score"] == 4
    assert flat["pain_points"] == "scaling"
    assert flat["signals_used"] == "/,/about"
