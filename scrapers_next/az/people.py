# import re
import lxml.html
from spatula import HtmlListPage, CSS, SelectorError

# XPath, URL
# from ..common.people import ScrapePerson


class BrokenHtmlListPage(HtmlListPage):
    def postprocess_response(self) -> None:
        # this page has a bad comment that makes the entire page parse incorrectly
        fixed_content = self.response.content.replace(b"--!>", b"-->")
        self.root = lxml.html.fromstring(fixed_content)
        if hasattr(self.source, "url"):
            self.root.make_links_absolute(self.source.url)  # type: ignore


class LegList(BrokenHtmlListPage):
    def process_item(self, item):
        try:
            name = CSS("a").match(item)[0].text_content()
        except SelectorError:
            self.skip("header row")

        print(name)

        # p = ScrapePerson(name=name)
        # return p


class SenList(LegList):
    source = "https://www.azleg.gov/memberroster/?body=S"
    selector = CSS("table tr")

    # def process_item(self, item):
    #     try:
    #         name = CSS("a").match(item)[0].text_content()
    #     except SelectorError:
    #         self.skip("header row")

    #     print(name)

    #     #p = ScrapePerson(name=name)
    #     # return p


class RepList(LegList):
    source = "https://www.azleg.gov/memberroster/?body=H"
    selector = CSS("table tr")
