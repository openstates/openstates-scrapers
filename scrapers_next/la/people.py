from spatula import HtmlListPage, CSS, URL
from openstates.models import ScrapePerson
import re


class Legislators(HtmlListPage):
    selector = CSS("fieldset div.media")

    def process_item(self, item):
        name_dirty = CSS("h4 span").match_one(item).text_content().strip()
        if re.search(r"Vacant", name_dirty):
            self.skip()
        name_dirty = name_dirty.split(", ")
        last_name = name_dirty[0]
        first_name = name_dirty[1]
        name = first_name + " " + last_name

        district = CSS("i.fa.fa-map").match_one(item).getnext().text_content().strip()
        party = CSS("i.fa.fa-users").match_one(item).getnext().text_content().strip()
        if party == "Democrat":
            party = "Democratic"
        email = CSS("a").match(item)[2].text_content().strip()
        img = CSS("img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="la",
            party=party,
            district=district,
            chamber=self.chamber,
            email=email,
            image=img,
        )

        p.add_source(self.source.url)

        return p


class Senate(Legislators):
    source = URL("https://senate.la.gov/Senators_FullInfo")
    chamber = "upper"


class House(Legislators):
    source = URL("https://house.louisiana.gov/H_Reps/H_Reps_FullInfo")
    chamber = "lower"
