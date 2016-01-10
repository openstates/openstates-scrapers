import os
import time
import requests
import urlparse
import functools
from OpenSSL.SSL import SysCallError

"""
API key must be passed as a header. You need the following headers to get JSON:
Authorization = your_apikey
Accept = "application/json"

If you're trying to hit api links through your browser you
need to install a header-modifying extension to do this, on firefox:
https://addons.mozilla.org/en-US/firefox/addon/modify-headers/
"""
class BadApiResponse(Exception):
    '''Raised if the service returns a service code higher than 400,
    other than 429. Makes the response object avaible as exc.resp
    '''
    def __init__(self, resp, *args):
        super(BadApiResponse, self).__init__(self, *args)
        self.resp = resp


def check_response(method):
    '''Decorated functions will run, and if they come back
    with a 429 and retry-after header, will wait and try again.
    '''
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        resp = method(self, *args, **kwargs)
        status = resp.status_code
        if 400 < status:
            if resp.status_code == 429:
                self.handle_429(resp, *args, **kwargs)
                return method(self, *args, **kwargs).json()
            msg_args = (resp, resp.text, resp.headers)
            msg = 'Bad api response: %r %r %r' % msg_args
            raise BadApiResponse(resp, msg)
        return resp.json()
    return wrapped


class ApiClient(object):
    '''
    docs: http://docs.api.iga.in.gov/
    '''
    root = "https://api.iga.in.gov/"
    resources = dict(
        sessions='/sessions',
        subjects='/{session}/subjects',
        chambers='/{session}/chambers',
        bills='/{session}/bills',
        bill='/{session}/bills/{bill_id}',
        chamber_bills='/{session}/chambers/{chamber}/bills',
        rollcalls='/{session}/rollcalls/{rollcall_id}', #note that rollcall_id has to be pulled off the URL, it's NOT the rollcall_number
        bill_actions='/{session}/bills/{bill_id}/actions',
        committees='/{session}/committees',
        committee='/{committee_link}',
        legislators='/{session}/legislators',
        legislator='/{session}/legislators/{legislator_id}',
        chamber_legislators='/{session}/chambers/{chamber}/legislators',
        bill_version = '/{session}/bills/{bill_id}/versions/{version_id}'
        )

    def __init__(self, scraper):
        self.scraper = scraper
        self.apikey = os.environ['INDIANA_API_KEY']

    @check_response
    def geturl(self, url):
        headers = {}
        headers['Authorization'] = self.apikey
        headers['Accept'] = "application/json"
        self.scraper.info('Api GET next page: %r, %r' % (url, headers))
        return self.scraper.get(url, headers=headers, verify=False)

    @check_response
    def get_relurl(self, url):
        headers = {}
        headers['Authorization'] = self.apikey
        headers['Accept'] = "application/json"
        url = urlparse.urljoin(self.root, url)
        self.scraper.info('Api GET: %r, %r' % (url, headers))
        return self.scraper.get(url, headers=headers, verify=False)

    def make_url(self, resource_name, **url_format_args):
        # Build up the url.
        url = self.resources[resource_name]
        url = url.format(**url_format_args)
        url = urlparse.urljoin(self.root, url)
        return url

    @check_response
    def get(self, resource_name, requests_args=None,
            requests_kwargs=None, **url_format_args):
        '''Resource is a self.resources dict key.
        '''
        num_bad_packets_allowed = 10
        url = self.make_url(resource_name, **url_format_args)

        # Add in the api key.
        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        requests_kwargs.update(verify=False)
        headers = requests_kwargs.get('headers', {})
        headers['Authorization'] = self.apikey
        headers['Accept'] = "application/json"
        requests_kwargs['headers'] = headers

        args = (url, requests_args, requests_kwargs)
        self.scraper.info('Api GET: %r, %r, %r' % args)
        resp = None
        tries = 0
        while resp is None and tries <  num_bad_packets_allowed:
            try:
                resp = self.scraper.get(url, *requests_args, **requests_kwargs)
            except SysCallError as e:
                err, string = e.args
                if err != 104:
                    raise
                tries += 1
                if tries >= num_bad_packets_allowed:
                    print err, string
                    raise RuntimeError("Got bad packet from API too many times, I give up")
        return resp

    def unpaginate(self, result):
        for data in result['items']:
            yield data
        while True:
            if 'nextLink' in result:
                url = result['nextLink']
                self.scraper.info('Api GET next page: %r' % url)
                result = self.get_relurl(url)
                if not result['items']:
                    return
                for data in result['items']:
                    yield data
            else:
                return

    def handle_429(self, resp, *args, **kwargs):
        '''According to the docs:

        "If the rate limit is exceeded, we will respond with a HTTP 429 Too Many
        Requests response code and a body that details the reason for the rate
        limiter kicking in. Further, the response will have a Retry-After
        header that tells you for how many seconds to sleep before retrying.
        You should anticipate this in your API client for the smoothest user
        experience."
        '''
        seconds = int(resp.headers['retry-after'])
        self.scraper.info('Got a 429: Sleeping %s seconds per retry-after header.' % seconds)
        time.sleep(seconds)
