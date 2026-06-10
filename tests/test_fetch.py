from icp.fetch import _extract, _strip_html, normalize_domain


def test_normalize_domain():
    assert normalize_domain("https://www.Foo.com/about") == "foo.com"
    assert normalize_domain("HTTP://Bar.io") == "bar.io"
    assert normalize_domain("  baz.com  ") == "baz.com"
    assert normalize_domain("www.qux.com/") == "qux.com"


def test_strip_html():
    assert _strip_html("<p>Hello   <b>world</b></p>") == "Hello world"


def test_extract_falls_back_on_thin_html():
    # Trafilatura returns nothing useful for a tiny snippet; we fall back to strip.
    html = "<html><body><span>Acme makes widgets</span></body></html>"
    out = _extract(html)
    assert "Acme makes widgets" in out


def test_extract_truncates(monkeypatch):
    from icp import config

    monkeypatch.setattr(config, "MAX_CHARS_PER_SOURCE", 10)
    html = "<p>" + "x" * 100 + "</p>"
    assert len(_extract(html)) <= 10
