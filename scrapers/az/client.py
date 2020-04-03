import requests


BASE_URL = "https://apps.azleg.gov/api"


class AZClient(object):
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def make_request(self, *segments, **params):
        url = "{}/{}".format(self.base_url, "/".join(segments))
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp

    def list_committees(self, **params):
        return self.make_request("Committee", **params)

    def get_standing_committee(self, **params):
        return self.make_request("StandingCommittee", **params)
