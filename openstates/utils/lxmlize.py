

class LXMLMixin(object):
    """
    Mixin for adding in LXML helper functions throughout Open States' code.

      - lxmlize
         Take a URL, load the URL into an LXML object, and make links
         absolute.
    """

    def lxmlize(self, url):
        text = self.urlopen(url)
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)
        return page
