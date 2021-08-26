from spatula import CSS, URL, HtmlListPage
from openstates.models import ScrapePerson
import re


class Legislators(HtmlListPage):
    selector = CSS("tbody tr")

    def process_item(self, item):
        name_dirty = CSS("td").match(item)[1].text_content().strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        party = CSS("td").match(item)[2].text_content().strip()
        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"

        district = CSS("td").match(item)[4].text_content().strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="tn",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        return p


class Senate(Legislators):
    source = URL("https://www.capitol.tn.gov/senate/members/")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.capitol.tn.gov/house/members/")
    chamber = "lower"
