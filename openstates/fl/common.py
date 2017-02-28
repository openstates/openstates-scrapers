import requests
import lxml.html


def url_xpath(url, path):
    doc = lxml.html.fromstring(requests.get(url).text)
    return doc.xpath(path)
