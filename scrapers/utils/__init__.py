import re

from openstates.scrape import Scraper
from .lxmlize import LXMLMixin  # noqa
from .lxmlize import url_xpath  # noqa
import hashlib
import uuid


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
