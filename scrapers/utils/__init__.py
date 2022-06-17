import regex

from .lxmlize import LXMLMixin  # noqa
from .lxmlize import url_xpath  # noqa

_phone_pattern = regex.compile(r"\(?\d{3}\)?\s?-?\d{3}-?\d{4}")
_email_pattern = regex.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\." r"[a-zA-Z]{2,}\b"
)


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
