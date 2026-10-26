import string
import os
import logging
from collections import defaultdict

import requests


class _RedactKey(logging.Filter):
    def __init__(self, key):
        super().__init__()
        self.key = key

    def filter(self, record):
        msg = record.getMessage()
        if self.key in msg:
            record.msg, record.args = msg.replace(self.key, "<key>"), ()
        return True


class OpenLegislationAPIClient(object):
    """
    Client for interfacing with the NY Senate's Open Legislation API.
    http://legislation.nysenate.gov/static/docs/html/index.html
    """

    root = "https://legislation.nysenate.gov/api/3/"
    resources = dict(
        bills=(
            "bills/{session_year}?limit={limit}&offset={offset}&full={full}"
            "&sort={sort_order}"
        ),
        bill=("bills/{session_year}/{bill_id}?summary={summary}&detail=" "{detail}"),
        bill_updates="bills/{session_year}/{bill_id}/updates?",
        updated_bills="bills/updates/{from_datetime}/{to_datetime}"
        "?summary={summary}&detail={detail}&limit={limit}&offset={offset}",
        committees=("committees/{session_year}/{chamber}?full={full}"),
        committee="committees/{session_year}/{chamber}/{committee_name}?",
        committee_history=(
            "committees/{session_year}/{chamber}/{committee_name}/history"
            "?limit={limit}&offset={offset}&full={full}&order={sort_order}"
        ),
        meetings=("agendas/meetings/{start}/{end}?limit=1000"),
        meeting=("agendas/{year}/{agenda_id}/{committee}?"),
        members=(
            "members/{session_year}?limit={limit}&offset={offset}&full={full}"
            "&sort={sort_order}"
        ),
        member="members/{session_year}/{member_id}?",
    )

    def _build_url(self, resource_name, **endpoint_format_args):
        endpoint = self.resources[resource_name]

        # Insert argument values into endpoint string. This technique
        # defaults values in the endpoint string to blank if they are
        # not specified in the given keyword arguments.
        endpoint = string.Formatter().vformat(
            endpoint, (), defaultdict(str, **endpoint_format_args)
        )

        # Build complete URL.
        url = self.root + endpoint

        return url

    def __init__(self, scraper):
        self.scraper = scraper
        self.api_key = os.environ["NEW_YORK_API_KEY"]
        # the key goes in params, which scrapelib's "GET - url" log line
        # leaves out, but connection errors still include the full URL
        logging.getLogger("scrapelib").addFilter(_RedactKey(self.api_key))

    def get(
        self, resource_name, requests_args=None, requests_kwargs=None, **url_format_args
    ):
        url = self._build_url(resource_name, **url_format_args)

        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        headers = requests_kwargs.get("headers", {})
        headers["Accept"] = "application/json"
        requests_kwargs["headers"] = headers
        requests_kwargs["params"] = {"key": self.api_key}
        if os.environ.get("HTTP_PROXY"):
            requests_kwargs["verify"] = False

        try:
            response = self.scraper.get(url, *requests_args, **requests_kwargs)
        except requests.RequestException as e:
            # error messages carry response.url, which includes the key
            raise RuntimeError(str(e).replace(self.api_key, "<key>")) from None
        return response.json()
