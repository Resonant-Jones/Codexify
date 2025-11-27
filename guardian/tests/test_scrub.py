# tests/test_scrub.py
import logging

from guardian.server.app import ScrubFormatter


def fmt(msg):
    h = logging.StreamHandler()
    h.setFormatter(ScrubFormatter("%(message)s"))
    lg = logging.getLogger("t")
    lg.handlers = []
    lg.addHandler(h)
    lg.setLevel(logging.INFO)
    return h.format(logging.LogRecord("t", logging.INFO, "", 0, msg, (), None))


def test_paths_and_secret_context():
    out = fmt(
        "cred at /x/y/token.json and client_secret plus API secret near credentials"
    )
    assert "token.json (hidden)" in out
    assert "client_secret (hidden)" in out
    assert (
        "API secret (hidden) is adjacent" in out
        or "API secret (hidden) near" in out
    )


def test_windows_and_mixed_case_paths():
    out = fmt(
        r"cred at C:\\Users\\me\\Downloads\\ToKeN.PiCkLe and /Keys/My.PEM plus CREDENTIALS.json"
    )
    # should mask common token/secret basenames, case-insensitive
    assert "token.pickle (hidden)" in out
    assert "my.pem (hidden)" in out
    assert "credentials.json (hidden)" in out


def test_plain_secret_word_not_masked_without_context():
    msg = "this sentence says secret but no credentials context"
    out = fmt(msg)
    # Should NOT auto-mask just the word 'secret' without nearby credentials context
    assert "secret (hidden)" not in out
    assert msg in out


def test_no_leak_of_original_paths():
    # Directory parts should be stripped; only basename should be shown with (hidden)
    msg = (
        "paths: /very/secret/path/token.json and /x/y/client_secret_oauth.json"
    )
    out = fmt(msg)
    assert "/very/secret/path/token.json" not in out
    assert "/x/y/client_secret_oauth.json" not in out
    assert "token.json (hidden)" in out
    assert "client_secret_oauth.json (hidden)" in out


def test_adjacent_secret_word_gets_masked_when_near_credentials():
    # When the word 'secret' is adjacent to credentials-like terms, it should be masked
    out = fmt("API secret near credentials and client_secret plus token.pickle")
    assert (
        "API secret (hidden) near" in out
        or "API secret (hidden) is adjacent" in out
    )
    assert "client_secret (hidden)" in out
    assert "token.pickle (hidden)" in out
