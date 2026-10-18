from vfetch.util import clean_url, fmt_elapsed, fmt_eta, fmt_rate, human_bytes, valid_url


def test_clean_and_valid_url():
    assert clean_url(' "https://example.com" ') == "https://example.com"
    assert valid_url("https://example.com/x")
    assert not valid_url("ftp://example.com")
    assert not valid_url("https://exa mple.com")
    assert not valid_url("")


def test_human_bytes():
    assert human_bytes(1024**2) == "1.0 MiB"
    assert human_bytes(None) == "—"
    assert human_bytes("garbage") == "—"


def test_fmt_rate():
    assert fmt_rate(1834562.7) == "1.7 MiB/s"
    assert fmt_rate(None) == "--"


def test_fmt_eta_and_elapsed():
    assert fmt_eta(65) == "01:05"
    assert fmt_eta(65.7) == "01:05"
    assert fmt_eta(None) == "--:--"
    assert fmt_eta("x") == "--:--"
    assert fmt_eta(3725) == "1:02:05"
    assert fmt_elapsed(3725.9) == "1:02:05"