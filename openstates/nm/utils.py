import urlparse


def get_abs_url(base_url, fetched_url):
    """
    This function will give us the absolute url for any href entry.

    base_url -- The url of the page where the relative url is found
    fetched_url -- the relative url
    """
    return urlparse.urljoin(base_url, fetched_url)
