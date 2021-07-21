from spatula import (
    JsonPage,
    URL,
)  # HtmlListPage, XPath, CSS, HtmlPage  # , SelectorError
from openstates.models import ScrapePerson
import os

"""
class LegDetailPage(JsonPage):
    def process_page(self):
        return p
"""


class LegListPage(JsonPage):
    def process_page(self):
        for item in self.data["items"]:
            self.process_item(item)

    def process_item(self, item):
        print(item)

        p = ScrapePerson(
            name="",
            state="in",
            chamber="",
            district="",
            party="",
            image="",
        )

        return p


class ApiGet(LegListPage):
    base_url = "http://iga.in.gov/legislative"
    api_base_url = "https://api.iga.in.gov"

    source = URL(
        "https://api.iga.in.gov/2021/legislators",
        headers={
            "Authorization": os.environ["INDIANA_API_KEY"],
            "User-Agent": "openstates 2021",
            "Accept": "application/json",
        },
    )
