import string
import os
import time
import functools
from collections import defaultdict
from OpenSSL.SSL import SysCallError


class BadAPIResponse(Exception):
    """
    Raised if the service returns a service code higher than 400,
    other than 429. Makes the response object available as exc.resp.
    """

    def __init__(self, resp, *args):
        super(BadAPIResponse, self).__init__(self, *args)
        self.resp = resp


def check_response(method):
    """
    Decorated functions will run, and if they come back with a 429
    and retry-after header, will wait and try again.
    """

    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        response = method(self, *args, **kwargs)
        status = response.status_code

        if status >= 400:
            if response.status_code == 429:
                self.handle_429(response, *args, **kwargs)
                return method(self, *args, **kwargs).json()
            msg_args = (response, response.text, response.headers)
            msg = "Bad api response: %r %r %r" % msg_args
            raise BadAPIResponse(response, msg)

        return response.json()

    return wrapped


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
        meetings=(
            "agendas/meetings/{start}/{end}?"
        ),
        meeting=(
            "agendas/{year}/{agenda_id}/{committee}?"
        ),
        members=(
            "members/{session_year}?limit={limit}&offset={offset}&full={full}"
            "&sort={sort_order}"
        ),
        member="members/{session_year}/{member_id}?",
    )

    def _build_url(self, resource_name, **endpoint_format_args):
        # Add API key to arguments to be placed into method call.
        endpoint = self.resources[resource_name] + "&key={api_key}"
        endpoint_format_args["api_key"] = self.api_key

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

    @check_response
    def get(
        self, resource_name, requests_args=None, requests_kwargs=None, **url_format_args
    ):
        num_bad_packets_allowed = 10
        url = self._build_url(resource_name, **url_format_args)

        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        headers = requests_kwargs.get("headers", {})
        headers["Accept"] = "application/json"
        requests_kwargs["headers"] = headers

        args = (url, requests_args, requests_kwargs)
        self.scraper.info("API GET: %r, %r, %r" % args)
        response = None
        tries = 0
        while response is None and tries < num_bad_packets_allowed:
            try:
                response = self.scraper.get(url, *requests_args, **requests_kwargs)
            except SysCallError as e:
                err, string = e.args
                if err != 104:
                    raise
                tries += 1
                if tries >= num_bad_packets_allowed:
                    print(err, string)
                    raise RuntimeError("Received too many bad packets from API.")

        return response

    def unpaginate(self, result):
        for data in result["items"]:
            yield data
        while True:
            if "nextLink" in result:
                url = result["nextLink"]
                self.scraper.info("API GET next page: {}".format(url))
                result = self.get_relurl(url)
                if not result["items"]:
                    return
                for data in result["items"]:
                    yield data
            else:
                return

    def handle_429(self, resp, *args, **kwargs):
        """
        According to the docs:

        'If the rate limit is exceeded, we will respond with a HTTP 429 Too Many
        Requests response code and a body that details the reason for the rate
        limiter kicking in. Further, the response will have a Retry-After
        header that tells you for how many seconds to sleep before retrying.
        You should anticipate this in your API client for the smoothest user
        experience.'
        """
        seconds = int(resp.headers["retry-after"])
        self.scraper.info(
            "Got a 429: Sleeping %s seconds per retry-after header." % seconds
        )
        time.sleep(seconds)
