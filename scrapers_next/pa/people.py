from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapePerson
import re


class LegList(HtmlListPage):
    selector = CSS("div.MemberInfoList-MemberWrapper")

    def process_item(self, item):
        name_dirty = CSS("a").match_one(item).text_content().strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        district = CSS("br").match_one(item).tail.strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        party = CSS("b").match_one(item).tail.strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"
        elif party == "(I)":
            party = "Independent"

        p = ScrapePerson(
            name=name,
            state="pa",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        return p


class Senate(LegList):
    source = URL(
        "https://www.legis.state.pa.us/cfdocs/legis/home/member_information/mbrList.cfm?body=S&sort=alpha"
    )
    chamber = "upper"


class House(LegList):
    source = URL(
        "https://www.legis.state.pa.us/cfdocs/legis/home/member_information/mbrList.cfm?body=H&sort=alpha"
    )
    chamber = "lower"
