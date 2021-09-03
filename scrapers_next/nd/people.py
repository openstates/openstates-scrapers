from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapePerson
import re


class LegList(HtmlListPage):
    source = URL(
        "https://www.legis.nd.gov/assembly/67-2021/members/members-by-district"
    )
    selector = CSS("div.view-content > div", num_items=142)

    def process_item(self, item):
        name = CSS("div.name").match_one(item).text_content().strip()
        name = re.search(r"(Senator|Representative)\s(.+)", name).groups()[1]

        chamber = CSS("div.chamber").match_one(item).text_content().strip()
        if chamber == "Senate":
            chamber = "upper"
        elif chamber == "House":
            chamber = "lower"

        for previous_tag in item.itersiblings(preceding=True):
            if previous_tag.get("class") == "title":
                district = previous_tag.text_content().strip()
                district = re.search(r"District\s(.+)", district).groups()[0]
                break

        party = CSS("div.party").match_one(item).text_content().strip()
        if party == "Democrat":
            party = "Democratic"

        p = ScrapePerson(
            name=name,
            state="nd",
            chamber=chamber,
            district=district,
            party=party,
        )

        return p
