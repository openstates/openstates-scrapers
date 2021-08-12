# import attr
from spatula import HtmlListPage, XPath, CSS

# from openstates.models import ScrapePerson


class LegList(HtmlListPage):
    def process_item(self, item):
        # print("hi", item.text_content())
        # for td in CSS("td").match(item):
        #     print("td.text ", td.text_content())
        district, name, url, party, __ = CSS("td").match(item)

        print("district", district.text_content())
        print(name.text_content())

        name = name.text_content().split(", ")
        name = name[1] + " " + name[0]
        name = name.replace("  ", " ")

        print("NAME", name)
        # TODO: nicer way to write this:
        if district.text_content().startswith("S"):
            district = district.text_content()[1:]
            if district.startswith("0"):
                district = district[1:]
        print("district ", district)

        party = party.text_content().strip()
        if party == "D":
            party = "Democrat"
        elif party == "R":
            party = "Republican"
        print("PARTY ", party)

        # p = ScrapePerson(
        #     name = name,
        #     state = "nj"
        # )


class SenList(LegList):
    selector = CSS("#content tbody tr")
    source = "https://www.cga.ct.gov/asp/menu/slist.asp"
    chamber = "upper"


class RepList(LegList):
    selector = XPath(
        "/html/body/table/tr[6]//p//a[contains(@href, 'BIO')][position()>40]",
        num_items=80,
    )
    source = "https://www.cga.ct.gov/asp/menu/hlist.asp"
    chamber = "lower"
