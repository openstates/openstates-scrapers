from .lxmlize import LXMLMixin
import re

def validate_email_address(email_address):
    is_valid = False

    email_pattern = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.'
                               r'[a-zA-Z]{2,}\b')
    email_match = email_pattern.match(email_address)
    if email_match is not None:
        is_valid = True

    return is_valid
