import requests
import lxml.html


class LXMLMixin(object):
    """
    Mixin for adding in LXML helper functions throughout Open States' code.

      - lxmlize
         Take a URL, load the URL into an LXML object, and make links
         absolute.
    """

    def lxmlize(self, url):
        try:
            text = self.get(url).text
        except requests.exceptions.SSLError:
            self.warning("`self.lxmlize()` failed due to SSL error, trying an unverified `requests.get()`")
            text = requests.get(url, verify=False).text
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)
        return page
