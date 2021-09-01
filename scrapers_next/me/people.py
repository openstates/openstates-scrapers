from spatula import URL, CSS, HtmlListPage, SelectorError

# from openstates.models import ScrapePerson
import re


class RepList(HtmlListPage):
    selector = CSS("table tr td", num_items=152)

    def process_item(self, item):
        name_dirty = CSS("br").match(item)[0].tail.strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]
        print(name)
        try:
            party = CSS("br").match(item)[2].tail.strip()
            if re.search(r"\(([A-Z])\s-(.+)", party):
                party = re.search(r"\(([A-Z])\s-(.+)", party).groups()[0]
            print(party)
        except SelectorError:
            pass

        # p = ScrapePerson(
        #     name=name,
        #     state="me",
        #     chamber=self.chamber,
        #     district=district,
        #     party=party,
        # )

        # return p


# class Senate(LegList):
#     source = URL("")
#     chamber = "upper"


class House(RepList):
    source = URL("https://legislature.maine.gov/house/house/MemberProfiles/ListAlpha")
    chamber = "lower"
