import os
import re
from urllib.parse import urljoin
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

    def get_session_no(self, session):
        session_no = ""
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        url = urljoin(self.root, f"/{session}")

        resp = requests.get(url, headers=headers, timeout=self.scraper.timeout).json()
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
        resp = requests.get(
            url,
            headers=headers,
            allow_redirects=False,
            timeout=self.scraper.timeout,
        )
        if "Location" in resp.headers:
            return resp.headers["Location"]

    def get_relurl(self, url):
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/pdf"
        headers["User-Agent"] = self.user_agent
        url = urljoin(self.root, url)
        self.scraper.info("Api GET: %r" % url)
        return self.scraper.get(url, headers=headers).json()

    # fetch an API url where we expect a redirect
    # return the new redirect URL (do not fetch it yet)
    def identify_redirect_url(self, url):
        if self.root not in url:
            url = urljoin(self.root, url)
        headers = {}
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        try:
            response = requests.get(
                url,
                headers=headers,
                allow_redirects=False,
                timeout=self.scraper.timeout,
            )
        except requests.RequestException as e:
            self.scraper.warning(f"Failed to fetch {url}: {e}")
            return None
        if response.status_code in (301, 302):
            return response.headers["Location"]
        else:
            self.scraper.warning(f"Failed to get expected redirect URL from {url}")
            return None

    def make_url(self, resource_name, **url_format_args):
        # Build up the url.
        url = self.resources[resource_name]
        url = url.format(**url_format_args)
        url = urljoin(self.root, url)
        return url

    def get(
        self, resource_name, requests_args=None, requests_kwargs=None, **url_format_args
    ):
        """Resource is a self.resources dict key."""
        url = self.make_url(resource_name, **url_format_args)

        # Add in the api key.
        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        headers = requests_kwargs.get("headers", {})
        headers["x-api-key"] = self.apikey
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self.user_agent
        requests_kwargs["headers"] = headers

        self.scraper.info("Api GET: %r" % url)
        return self.scraper.get(url, *requests_args, **requests_kwargs).json()

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
