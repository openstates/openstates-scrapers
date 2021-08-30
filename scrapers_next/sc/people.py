from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapePerson
import re


class Legislators(HtmlListPage):
    selector = CSS("div.member")

    def process_item(self, item):
        name = CSS("a.membername").match_one(item).text_content()
        name = re.search(r"(Senator|Representative)\s(.+)", name).groups()[1]

        party = CSS("a.membername").match_one(item).tail.strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"

        district = CSS("div.district a").match_one(item).text_content().strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="sc",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("div.district a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        img = CSS("img").match_one(item).get("src")
        p.image = img

        return p


class Senate(Legislators):
    source = URL("https://www.scstatehouse.gov/member.php?chamber=S")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.scstatehouse.gov/member.php?chamber=H")
    chamber = "lower"
