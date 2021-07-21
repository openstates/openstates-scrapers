from spatula import (
    JsonPage,
    URL,
    HtmlPage,
    CSS,
)  # HtmlListPage, XPath, CSS, HtmlPage  # , SelectorError
from openstates.models import ScrapePerson
import os


class LegDetailPage(HtmlPage):
    def process_page(self):
        p = self.input
        img = CSS("div .row-fluid.span2.hidden-print img").match_one(self.root)
        p.image = img
        # district
        # address
        # phone

        return p


class LegListPage(JsonPage):
    def process_page(self):
        for item in self.data["items"]:
            yield self.process_item(item)

    def process_item(self, item):
        name = item["firstName"] + " " + item["lastName"]
        party = item["party"]

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district="",
            party=party,
            image="",
        )

        p.family_name = item["lastName"]
        p.given_name = item["firstName"]

        # link from old code (no authentication needed?)
        # getting 503 response
        base_url = "http://iga.in.gov/legislative"
        api_base_url = "https://api.iga.in.gov"
        api_link = api_base_url + item["link"]
        html_link = base_url + item["link"].replace(
            "legislators/", "legislators/legislator_"
        )
        print(api_link)
        print(html_link)
        detail_source = URL(html_link)

        # this is my logic from api
        # getting a 403 error
        """
        print(item["link"])
        link_id = item["link"].split("/")[-1]
        link_id = link_id.split("_")[-1]
        print(link_id)
        detail_link = "https://api.iga.in.gov/2021/legislators/" + link_id
        detail_link = "https://api.iga.in.gov" + item["link"]
        print(detail_link)
        """

        p.add_source(self.source.url)
        # p.add_source(detail_link)
        # p.add_link(detail_link, note="homepage")

        return LegDetailPage(p, source=detail_source)


class Senate(LegListPage):
    chamber = "upper"
    source = URL(
        "https://api.iga.in.gov/2021/chambers/senate/legislators",
        headers={
            "Authorization": os.environ["INDIANA_API_KEY"],
            "User-Agent": "openstates 2021",
            "Accept": "application/json",
        },
    )


class House(LegListPage):
    chamber = "lower"
    source = URL(
        "https://api.iga.in.gov/2021/chambers/house/legislators",
        headers={
            "Authorization": os.environ["INDIANA_API_KEY"],
            "User-Agent": "openstates 2021",
            "Accept": "application/json",
        },
    )
