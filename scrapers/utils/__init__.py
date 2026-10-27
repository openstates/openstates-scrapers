import re
import ssl
import time

import requests
from openstates.scrape import Scraper
from .lxmlize import LXMLMixin  # noqa
from .lxmlize import url_xpath  # noqa
import hashlib
import uuid


class SSLRetryMixin:
    """Retry requests that fail with an SSLError, which scrapelib re-raises
    without retrying (e.g. a server dropping the connection mid-handshake).

    Certificate verification failures are raised at once, so callers like
    LXMLMixin.lxmlize can still fall back to verify=False.
    """

    def request(self, method, url, **kwargs):
        for attempt in range(self.retry_attempts + 1):
            try:
                return super().request(method, url, **kwargs)
            except requests.exceptions.SSLError as e:
                if attempt == self.retry_attempts or _is_cert_error(e):
                    raise
                wait = self.retry_wait_seconds * 2**attempt
                self.warning(f"{e}, retrying in {wait}s")
                time.sleep(wait)


def _is_cert_error(e):
    while e is not None:
        if isinstance(e, ssl.SSLCertVerificationError):
            return True
        e = e.__cause__ or e.__context__
    return False


def get_session_meta(scraper: Scraper, identifier: str):
    for i in scraper.jurisdiction.legislative_sessions:
        if i["identifier"] == identifier:
            return i


def hash_key(key_str):
    """
    Used to shorten identifier strings while maintaining uniqueness.
    :param key_str: type str - identifier of variable length
    :return: type str - unique hash of identifier
    """
    hash_val = hashlib.md5()
    hash_val.update(key_str.encode("utf-8"))
    hex_encoded_hash = hash_val.hexdigest()
    uuid_hex = uuid.UUID(hex_encoded_hash)
    unique_event_hash_str = str(uuid_hex)
    return unique_event_hash_str


_phone_pattern = re.compile(r"\(?\d{3}\)?\s?-?\d{3}-?\d{4}")
_email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\." r"[a-zA-Z]{2,}\b")


def validate_phone_number(phone_number):
    is_valid = False

    # Phone format validation regex.
    phone_match = _phone_pattern.match(phone_number)
    if phone_match is not None:
        is_valid = True

    return is_valid


def validate_email_address(email_address):
    is_valid = False

    email_match = _email_pattern.match(email_address)
    if email_match is not None:
        is_valid = True

    return is_valid
