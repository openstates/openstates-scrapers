

class LXMLMixin(object):
    """
    """

    def lxmlize(self, url):
        text = self.urlopen(url)
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)
        return page
