import subprocess
import lxml.html


class LXMLMixinOK(object):
    def curl_lxmlize(self, url):
        """Parses document into an LXML object and makes links absolute.
        Outsources to curl as a workaround for the python ssl module's lack of
        out-of-the-box handling of TLS 1.0 servers.

        Args:
            url (str): URL of the document to parse.
        Returns:
            Element: Document node representing the page.
        """

        self.info("GET via curl subprocess: " + url)
        response = subprocess.run(["curl", "--silent", url], stdout=subprocess.PIPE)
        page = lxml.html.fromstring(response.stdout)
        page.make_links_absolute(url)

        return page
