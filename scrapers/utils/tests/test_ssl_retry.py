import ssl

import requests
import scrapelib
from requests.adapters import BaseAdapter

from .. import SSLRetryMixin


def ssl_error(cause):
    try:
        raise cause
    except Exception:
        try:
            raise requests.exceptions.SSLError("wrapped")
        except requests.exceptions.SSLError as e:
            return e


class FlakyAdapter(BaseAdapter):
    def __init__(self, errors):
        super().__init__()
        self.errors = list(errors)
        self.calls = 0

    def send(self, request, **kwargs):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"ok"
        resp.url = request.url
        resp.request = request
        return resp

    def close(self):
        pass


class Scraper(SSLRetryMixin, scrapelib.Scraper):
    def warning(self, msg):
        pass


def scraper(errors):
    s = Scraper(retry_attempts=2, retry_wait_seconds=0, requests_per_minute=0)
    s.cache_write_only = False
    adapter = FlakyAdapter(errors)
    s.mount("https://", adapter)
    return s, adapter


def test_retries_handshake_errors():
    s, adapter = scraper([ssl_error(ssl.SSLEOFError()), ssl_error(ssl.SSLError())])
    assert s.get("https://example.com/").text == "ok"
    assert adapter.calls == 3


def test_gives_up_after_retry_attempts():
    errors = [ssl_error(ssl.SSLEOFError()) for _ in range(3)]
    s, adapter = scraper(errors)
    try:
        s.get("https://example.com/")
        assert False, "expected SSLError"
    except requests.exceptions.SSLError:
        pass
    assert adapter.calls == 3


def test_does_not_retry_cert_errors():
    s, adapter = scraper([ssl_error(ssl.SSLCertVerificationError())])
    try:
        s.get("https://example.com/")
        assert False, "expected SSLError"
    except requests.exceptions.SSLError:
        pass
    assert adapter.calls == 1
