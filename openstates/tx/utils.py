import re


def parse_ftp_listing(text):
    lines = text.strip().split('\r\n')
    return (' '.join(line.split()[3:]) for line in lines if line)


_phone_pattern = r'\(?\d+\)?[- ]?\d{3}[-.]\d{4}'
_phone_re = re.compile(_phone_pattern + '(?! Fax)', re.IGNORECASE)
_fax_re = re.compile(
    r'(?<=Fax: )%s|%s(?= \(f\)| Fax)' % (_phone_pattern, _phone_pattern),
    re.IGNORECASE
)


def extract_phone(string):
    return next(iter(_phone_re.findall(string)), None)


def extract_fax(string):
    return next(iter(_fax_re.findall(string)), None)
