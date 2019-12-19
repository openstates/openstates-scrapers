import requests
import lxml.html


def url_xpath(url, path, verify=True):
    doc = lxml.html.fromstring(requests.get(url, verify=verify).text)
    return doc.xpath(path)


class LXMLMixin(object):
    """Mixin for adding LXML helper functions to Open States code."""

    def lxmlize(self, url, raise_exceptions=False):
        """Parses document into an LXML object and makes links absolute.

        Args:
            url (str): URL of the document to parse.
        Returns:
            Element: Document node representing the page.
        """
        try:
            # This class is always mixed into subclasses of `Scraper`,
            # which have a `get` method defined.
            response = self.get(url)
        except requests.exceptions.SSLError:
            self.warning(
                "`self.lxmlize()` failed due to SSL error, trying "
                "an unverified `self.get()` (i.e. `requests.get()`)"
            )
            response = self.get(url, verify=False)

        if raise_exceptions:
            response.raise_for_status()

        page = lxml.html.fromstring(response.text)
        page.make_links_absolute(url)

        return page

    def get_node(self, base_node, xpath_query):
        """Searches for node in an element tree.

        Attempts to return only the first node found for an xpath query. Meant
        to cut down on exception handling boilerplate.

        Args:
            base_node (Element): Document node to begin querying from.
            xpath_query (str): XPath query to define nodes to search for.
        Returns:
            Element: First node found that matches the query.
        """
        try:
            node = base_node.xpath(xpath_query)[0]
        except IndexError:
            node = None

        return node

    def get_nodes(self, base_node, xpath_query):
        """Searches for nodes in an element tree.

        Attempts to return all nodes found for an xpath query. Meant to cut
        down on exception handling boilerplate.

        Args:
            base_node (Element): Document node to begin querying from.
            xpath_query (str): Xpath query to define nodes to search for.
        Returns:
            List[Element]: All nodes found that match the query.
        """
        return base_node.xpath(xpath_query)
