from icp import cache
from icp.schema import Confidence, EmployeeBucket, EnrichmentRecord, EnrichmentResult


def _record(domain="acme.com", score=4):
    return EnrichmentRecord(
        domain=domain,
        result=EnrichmentResult(
            company_name="Acme",
            what_it_does="Sells widgets.",
            industry="Manufacturing",
            employee_count_estimate=EmployeeBucket.M,
            icp_fit_score=score,
            icp_fit_reasoning="reason",
            buyer_persona="VP Eng",
            pain_points=["a", "b"],
            confidence=Confidence.MEDIUM,
        ),
        model="gemini-2.5-flash",
        prompt_version="v1",
        signals_used=["/", "/about"],
    )


def test_signals_roundtrip(tmp_path):
    db = tmp_path / "t.db"
    assert cache.get_signals("acme.com", db) is None
    cache.set_signals("acme.com", {"/": "hello"}, db)
    assert cache.get_signals("acme.com", db) == {"/": "hello"}


def test_result_roundtrip(tmp_path):
    db = tmp_path / "t.db"
    rec = _record()
    assert cache.get_result("acme.com", "v1", "gemini-2.5-flash", db) is None
    cache.set_result(rec, db)
    got = cache.get_result("acme.com", "v1", "gemini-2.5-flash", db)
    assert got is not None
    assert got.result.icp_fit_score == 4
    assert got.signals_used == ["/", "/about"]


def test_prompt_version_isolation(tmp_path):
    db = tmp_path / "t.db"
    cache.set_result(_record(score=4), db)
    # Different prompt version -> cache miss, no clobber.
    assert cache.get_result("acme.com", "v2", "gemini-2.5-flash", db) is None
    assert cache.get_result("acme.com", "v1", "gemini-2.5-flash", db).result.icp_fit_score == 4
