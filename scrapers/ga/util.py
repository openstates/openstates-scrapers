from suds.client import Client
import logging
import socket
import urllib.error
import time
import suds

logging.getLogger("suds").setLevel(logging.WARNING)
log = logging.getLogger("openstates")


url = "http://webservices.legis.ga.gov/GGAServices/%s/Service.svc?wsdl"


def get_client(service):
    client = backoff(Client, get_url(service), autoblend=True)
    return client


def get_url(service):
    return url % (service)


def backoff(function, *args, **kwargs):
    retries = 5

    def _():
        time.sleep(1)  # Seems like their server can't handle the load.
        return function(*args, **kwargs)

    for attempt in range(retries):
        try:
            return _()
        except (socket.timeout, urllib.error.URLError, suds.WebFault) as e:
            if "This Roll Call Vote is not published." in str(e):
                raise ValueError("Roll Call Vote isn't published")

            backoff = (attempt + 1) * 15
            log.warning(
                "[attempt %s]: Connection broke. Backing off for %s seconds."
                % (attempt, backoff)
            )
            log.info(str(e))
            time.sleep(backoff)

    raise ValueError("The server's not playing nice. We can't keep slamming it.")


# available via the session dropdown on
# http://www.legis.ga.gov/Legislation/en-US/Search.aspx
SESSION_SITE_IDS = {
    "2021_22": 1029,
    "2020_ss": "1027",
    "2019_20": 27,
    "2018_ss": 26,
    "2017_18": 25,
    "2015_16": 24,
    "2013_14": 23,
    "2011_ss": 22,
    "2011_12": 21,
}
