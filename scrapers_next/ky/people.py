from spatula import CSS, HtmlListPage, URL
from openstates.models import ScrapePerson


class LegList(HtmlListPage):
    selector = CSS("a.Legislator-Card.col-md-4.col-sm-6.col-xs-12")

    def process_page(self, item):
        name = CSS("h3").match_one(item).text_content()
        print(name)

        p = ScrapePerson(
            name=name,
            state="ky",
            party="",
            chamber=self.chamber,
            district="",
            image="",
        )

        return p


class Senate(LegList):
    source = URL("https://legislature.ky.gov/Legislators/senate")
    chamber = "upper"


class House(LegList):
    source = URL("https://legislature.ky.gov/Legislators/house-of-representatives")
    chamber = "lower"
