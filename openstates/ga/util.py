from suds.client import Client
import logging
import socket
import urllib2
import time

logging.getLogger('suds').setLevel(logging.WARNING)
log = logging.getLogger('billy')


url = 'http://webservices.legis.ga.gov/GGAServices/%s/Service.svc?wsdl'


def get_client(service):
    client = Client(get_url(service))
    return client


def get_url(service):
    return url % (service)


def backoff(function, *args, **kwargs):
    retries = 5
    nice = 0

    def _():
        time.sleep(1)  # Seems like their server can't handle the load.
        return function(*args, **kwargs)

    for attempt in range(retries):
        try:
            return _()
        except (socket.timeout, urllib2.URLError) as e:
            backoff = (attempt * 15)
            log.warning(
                "[attempt %s]: Connection broke. Backing off for %s seconds." % (
                    attempt,
                    backoff
                )
            )
            log.info(str(e))
            time.sleep(backoff)

    raise ValueError(
        "The server's not playing nice. We can't keep slamming it."
    )
