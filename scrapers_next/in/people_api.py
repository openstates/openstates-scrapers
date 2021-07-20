from spatula import (
    JsonListPage,
    # JsonPage,
    URL,
)  # HtmlListPage, XPath, CSS, HtmlPage  # , SelectorError
from openstates.models import ScrapePerson

"""
class LegDetailPage(JsonPage):
    def process_page(self):
        return p
"""


class LegListPage(JsonListPage):
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
        "https://api.iga.in.gov/122/legislators", headers={"Authorization": "Token"}
    )
