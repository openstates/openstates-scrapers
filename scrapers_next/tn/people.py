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

        detail_link = CSS("td a").match(item)[1].get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        email = CSS("td a").match(item)[0].get("href")
        email = re.search(r"mailto:(.+)", email).groups()[0]
        p.email = email

        # should this be appended to an address?
        office_room = CSS("td").match(item)[5].text_content().strip()
        p.extras["office"] = office_room

        return p


class Senate(Legislators):
    source = URL("https://www.capitol.tn.gov/senate/members/")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.capitol.tn.gov/house/members/")
    chamber = "lower"
