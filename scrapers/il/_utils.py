import urllib


def canonicalize_url(url):
    url = url.replace("/../", "/")
    o = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qsl(o.query)
    qs = sorted((upperfirst(k), v) for k, v in qs)

    canonical_o = list(o)
    canonical_o[4] = urllib.parse.urlencode(qs)
    return urllib.parse.urlunparse(canonical_o)


def upperfirst(x):
    return x[0].upper() + x[1:]
