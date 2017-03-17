import requests
import lxml.html


def url_xpath(url, path, requester=requests):
    doc = lxml.html.fromstring(requester.get(url).text)
    return doc.xpath(path)


SESSION_SITE_IDS = {
    '2010': '101',
    '2011': '111',
    '2011specialI': '112',
    '2012': '121',
    '2012specialI': '122',
    '2013': '131',
    '2013specialI': '132',
    '2014': '141',
    '2014specialI': '142',
    '2015': '151',
    '2015specialI': '152',
    '2016': '161',
    '2017': '171',
}
