
def last_name_first_name_to_full_name(last_name_first_name):
    """Convert a name in the format 'Last, First' to 'First Last'

    Warning: Make sure that the names on the page you are scraping are consistently formatted. Some
    legislator sites are inconsistent in where they place the middle name, suffixes, and commas.
    """
    last, first = map(str.strip, last_name_first_name.split(','))
    return '{first} {last}'.format(first=first, last=last)
