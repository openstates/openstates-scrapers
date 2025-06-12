import os
import re
import time
from urllib.parse import urljoin
import functools
import requests

"""
API key must be passed as a header. You need the following headers to get JSON:
x-api-key = your_apikey
Accept = "application/json"

If you're trying to hit api links through your browser you
need to install a header-modifying extension to do this, on firefox:
https://addons.mozilla.org/en-US/firefox/addon/modify-headers/
"""
settings = dict(SCRAPELIB_TIMEOUT=300)


class BadApiResponse(Exception):
    """Raised if the service returns a service code higher than 400,
    other than 429. Makes the response object available as exc.resp
    """

    def __init__(self, resp, *args):
        super(BadApiResponse, self).__init__(self, *args)
        self.resp = resp


def check_response(method):
    """Decorated functions will run, and if they come back
    with a 429 and retry-after header, will wait and try again.
    """

    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        resp = method(self, *args, **kwargs)
        status = resp.status_code
        if 400 < status:
            if resp.status_code == 429:
                self.handle_429(resp, *args, **kwargs)
                return method(self, *args, **kwargs).json()
            msg_args = (resp, resp.text, resp.headers)
            msg = "Bad api response: %r %r %r" % msg_args
            raise BadApiResponse(resp, msg)
        return resp.json()

    return wrapped


class ApiClient(object):
    """
    docs: https://docs.api.iga.in.gov/
    """

    root = "https://api.iga.in.gov"
    resources = dict(
        sessions="/",
        session="/{session}",
        subjects="/{session}/subjects",
        chambers="/{session}/chambers",
        bills="/{session}/bills",
        bill="{bill_link}",
        chamber_bills="/{session}/chambers/{chamber}/bills",
        rollcalls="/{session}/rollcalls",
        rollcall="{rollcall_link}",
        meetings="/{session}/meetings",
        meeting="{meeting_link}",
        bill_actions="{action_link}",
        committees="/{session}/committees",
        committee="{committee_link}",
        legislators="/{session}/legislators",
        legislator="{legislator_link}",
        chamber_legislators="/{session}/chambers/{chamber}/legislators",
        bill_version="/{session}/bills/{bill_id}/versions/{version_id}",
        fiscal_notes="/{session}/fiscal-notes",
        document="{doc_link}",
    )

    def __init__(self, scraper):
        self.scraper = scraper
        self.apikey = os.environ["INDIANA_API_KEY"]
        self.user_agent = os.getenv("USER_AGENT", "openstates")
        # On 2025-06-12 IN TLS certificate expired, so we need to use verify=False
        # If this is fixed in the future, this can be changed to True here and in __init__
        self.verify = False

    def get_session_no(self, session):
        session_no = ""
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        url = urljoin(self.root, f"/{session}")

        resp = requests.get(url, headers=headers, verify=self.verify).json()
        if "message" in resp:
            raise Exception(resp["message"])
        session_no_regex = re.search(r"Session\s+(\d+).+", resp["name"])
        if session_no_regex:
            session_no = session_no_regex.group(1)
        else:
            raise Exception("Invalid session")

        return session_no

    def get_document_url(self, url):
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/pdf"
        headers["User-Agent"] = self.user_agent
        url = urljoin(self.root, url)
        resp = requests.get(url, headers=headers, allow_redirects=False, verify=self.verify)
        if "Location" in resp.headers:
            return resp.headers["Location"]

    @check_response
    def geturl(self, url):
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        self.scraper.info("Api GET next page: %r, %r" % (url, headers))
        return self.scraper.get(url, headers=headers)

    @check_response
    def get_relurl(self, url):
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/pdf"
        headers["User-Agent"] = self.user_agent
        url = urljoin(self.root, url)
        self.scraper.info("Api GET: %r, %r" % (url, headers))
        return self.scraper.get(url, headers=headers)

    # fetch an API url where we expect a redirect
    # return the new redirect URL (do not fetch it yet)
    def identify_redirect_url(self, url):
        if self.root not in url:
            url = urljoin(self.root, url)
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        response = requests.get(url, headers=headers, allow_redirects=False, verify=self.verify)
        if response.status_code in (301, 302):
            return response.headers["Location"]
        else:
            self.scraper.error(f"Failed to get expected redirect URL from {url}")
            return None

    def make_url(self, resource_name, **url_format_args):
        # Build up the url.
        url = self.resources[resource_name]
        url = url.format(**url_format_args)
        url = urljoin(self.root, url)
        return url

    @check_response
    def get(
        self, resource_name, requests_args=None, requests_kwargs=None, **url_format_args
    ):
        """Resource is a self.resources dict key."""
        num_bad_packets_allowed = 10
        url = self.make_url(resource_name, **url_format_args)

        # Add in the api key.
        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        headers = requests_kwargs.get("headers", {})
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        requests_kwargs["headers"] = headers

        args = (url, requests_args, requests_kwargs)
        self.scraper.info("Api GET: %r, %r, %r" % args)
        resp = None
        tries = 0
        while resp is None and tries < num_bad_packets_allowed:
            resp = self.scraper.get(url, *requests_args, verify=self.verify, **requests_kwargs)
        return resp

    def unpaginate(self, result):
        for data in result["items"]:
            yield data
        while True:
            if "nextLink" in result:
                url = result["nextLink"]
                # pagination is broken somehow
                url = url.replace("per_page=50", "")
                self.scraper.info("Api GET next page: %r" % url)
                result = self.get_relurl(url)
                if not result["items"]:
                    return
                for data in result["items"]:
                    yield data
            else:
                return

    def handle_429(self, resp, *args, **kwargs):
        """According to the docs:

        "If the rate limit is exceeded, we will respond with a HTTP 429 Too Many
        Requests response code and a body that details the reason for the rate
        limiter kicking in. Further, the response will have a Retry-After
        header that tells you for how many seconds to sleep before retrying.
        You should anticipate this in your API client for the smoothest user
        experience."
        """
        seconds = int(resp.headers["retry-after"])
        self.scraper.info(
            "Got a 429: Sleeping %s seconds per retry-after header." % seconds
        )
        time.sleep(seconds)
