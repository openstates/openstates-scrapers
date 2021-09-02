from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapePerson
import re


class LegList(HtmlListPage):
    selector = CSS("div.col-xs-6.col-sm-3.col-md-2.col-lg-2")

    def process_item(self, item):
        name_party = CSS("span").match(item)[0].text_content().strip().split(" - ")
        name = name_party[0].strip()
        party = name_party[1].strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"
        elif party == "(DTS)":
            party = "Independent"

        district = CSS("span").match(item)[1].text_content().strip()
        district = re.search(r"District:\s(.+)", district).groups()[0].strip()

        p = ScrapePerson(
            name=name,
            state="nm",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        img = CSS("img").match_one(item).get("src")
        p.image = img

        return p


class Senate(LegList):
    source = URL("https://www.nmlegis.gov/Members/Legislator_List?T=S")
    chamber = "upper"


class House(LegList):
    source = URL("https://www.nmlegis.gov/Members/Legislator_List?T=R")
    chamber = "lower"
