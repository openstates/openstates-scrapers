OK_PROXY = 'https://dcyqmf3d8vr92.cloudfront.net'


def proxy_house_url(url):
    return url.replace('http://www.okhouse.gov', OK_PROXY)
