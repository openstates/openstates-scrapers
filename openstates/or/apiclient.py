import os

import requests


class OregonLegislatorODataClient(object):
    """
    Client for interfacing with Oregon Legislator OData API.
    https://www.oregonlegislature.gov/citizen_engagement/Pages/data.aspx
    """

    root = 'https://api.oregonlegislature.gov/odata/odataservice.svc/'
    resources = dict(
        sessions='LegislativeSessions',
        legislators='LegislativeSessions(\'{session}\')/Legislators',
    )

    def _build_url(self, resource_name, **endpoint_format_args):
        endpoint = self.resources[resource_name]
        endpoint = endpoint.format(**endpoint_format_args)

        url = self.root + endpoint
        return url

    def __init__(self, scraper):
        self.scraper = scraper
        self.username = os.environ['OLODATA_USERNAME']
        self.password = os.environ['OLODATA_PASSWORD']

    def get(self, resource_name, requests_args=None,
            requests_kwargs=None, **url_format_args):
        num_bad_packets_allowed = 10
        url = self._build_url(resource_name, **url_format_args)

        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        requests_kwargs.update(verify=True)
        requests_kwargs.update(auth=(self.username, self.password))
        headers = requests_kwargs.get('headers', {})
        headers['Accept'] = "application/json"
        requests_kwargs['headers'] = headers

        response = None

        tries = 0
        while response is None and tries < num_bad_packets_allowed:
            try:
                response = self.scraper.get(url, *requests_args,
                                            **requests_kwargs)
            except requests.exceptions.RequestException as e:
                err, string = e.args
                print('warn: retry')
                tries += 1
                if tries >= num_bad_packets_allowed:
                    print(err, string)
                    raise RuntimeError('Received too many bad packets from API.')

        return response.json()['value']
