from spatula import HtmlListPage, XPath, CSS  # , CSS, , URL
from openstates.models import ScrapePerson


class LegList(HtmlListPage):
    def process_item(self, item):
        # name = item.text_content()
        name = CSS("div a").match(item)[1].text_content()
        district = (
            CSS("div .esg-content.eg-senators-grid-element-1")
            .match_one(item)
            .text_content()
        )
        img = CSS("div img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district=district,
            party=self.party,
            image=img,
        )
        return p


class RedRepList(LegList):
    source = "https://www.indianahouserepublicans.com/members/"
    # selector = CSS("", num_items=)
    chamber = "lower"
    party = "republican"


class BlueRepList(LegList):
    source = "https://indianahousedemocrats.org/members"
    # selector = CSS("", num_items=)
    chamber = "lower"
    party = "democratic"


class BlueSenList(LegList):
    source = "https://www.indianasenatedemocrats.org/senators/"
    selector = XPath(".//*[@id='esg-grid-10-1']/div/ul/li")
    chamber = "upper"
    party = "democratic"


class RedSenList(LegList):
    source = "https://www.indianasenaterepublicans.com/senators"
    # selector = CSS("", num_items=)
    chamber = "upper"
    party = "republican"
