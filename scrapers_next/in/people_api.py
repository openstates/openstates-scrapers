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
        firstname = item["firstName"]
        # lastname = item["lastName"]
        # party = item["party"]
        # link = item["link"]
        print(firstname)

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
        "https://api.iga.in.gov/122/chambers/senate/legislators",
        headers={
            "Authorization": "Token a62cb5ec0dcb321f9ac33802160911556c6cbb19",
            "Accept": "application/json",
        },
    )
