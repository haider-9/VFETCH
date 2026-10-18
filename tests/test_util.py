from vfetch.util import clean_url, valid_url, human_bytes, fmt_eta
def test_util():
    assert clean_url(' "https://example.com" ') == "https://example.com"
    assert valid_url("https://example.com/x") and not valid_url("ftp://example.com")
    assert human_bytes(1024**2) == "1.0 MiB" and fmt_eta(65) == "01:05"
