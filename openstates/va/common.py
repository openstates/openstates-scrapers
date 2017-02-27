import requests
import lxml.html


def url_xpath(url, path, requester=requests):
    doc = lxml.html.fromstring(requester.get(url).text)
    return doc.xpath(path)
