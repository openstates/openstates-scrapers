import requests

from mi import Michigan


SUCCESS_HTML = """
<html><body>
<select name="sessions" id="session_B">
<option value="All">All</option>
<option value="2025-2026" selected="selected">2025-2026</option>
<option value="2023-2024">2023-2024</option>
<option value="2011-2012">2011-2012</option>
</select>
</body></html>
"""

# legislature.mi.gov's WAF returns a page like this (no <option> elements)
# instead of the real search page when it challenges a request.
CAPTCHA_HTML = """
<html><body style="font-family:times;color:white;font-size:15px;" bgcolor="#405f8d">
<title>Validation request</title>
<h3 align="center">User validation required to continue..</h3>
</body></html>
"""


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error")


def test_get_session_list_returns_scraped_sessions_on_success(monkeypatch):
    monkeypatch.setattr(
        "mi.requests.get", lambda url, headers=None: FakeResponse(SUCCESS_HTML)
    )

    sessions = Michigan().get_session_list()

    assert sessions
    assert "2025-2026" in sessions


def test_get_session_list_falls_back_when_request_fails(monkeypatch):
    def raise_connection_error(url, headers=None):
        raise requests.exceptions.ConnectionError("could not connect")

    monkeypatch.setattr("mi.requests.get", raise_connection_error)

    sessions = Michigan().get_session_list()

    assert sessions
    assert "2025-2026" in sessions


def test_get_session_list_falls_back_when_waf_challenge_page_returned(monkeypatch):
    # Reproduces the actual OPEN-17 failure: a 200 response whose body is a
    # CAPTCHA challenge page with zero <option> elements.
    monkeypatch.setattr(
        "mi.requests.get", lambda url, headers=None: FakeResponse(CAPTCHA_HTML)
    )

    sessions = Michigan().get_session_list()

    assert sessions
    assert "2025-2026" in sessions
