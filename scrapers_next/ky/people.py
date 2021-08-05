from spatula import CSS, HtmlListPage, URL, HtmlPage, SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("img.leg-img").match_one(self.root).get("src")
        p.image = img

        title = (
            CSS("div .row.profile-top h3").match_one(self.root).text_content().strip()
        )
        if title != "":
            p.extras["title"] = title

        counties = CSS("div .center ul li").match(self.root).text_content()
        counties = re.search(r"(.+)\s\(Part\)", counties).groups()[0]
        counties = counties.split(", ")
        p.extras["counties represented"] = counties

        email = CSS("p.title").match(self.root)[14].getnext().text_content()
        p.email = email

        try:
            twitter = CSS("p.title").match(self.root)[15].getnext().text_content()
            p.ids["twitter"] = twitter.lstrip("@")
        except SelectorError:
            twitter = None

        # Mailing, Legislative, and Capitol
        len(CSS("address").match(self.root))

        return p


class LegList(HtmlListPage):
    selector = CSS("a.Legislator-Card.col-md-4.col-sm-6.col-xs-12")

    def process_item(self, item):
        name = CSS("h3").match_one(item).text_content()
        if name == " - Vacant Seat":
            self.skip()

        party = CSS("small").match_one(item).text_content()
        if party == "Democrat":
            party = "Democratic"

        district = CSS("p").match(item)[0].text_content()
        district = re.search(r"District:\r\n(.+)", district).groups()[0].strip()

        p = ScrapePerson(
            name=name,
            state="ky",
            party=party,
            chamber=self.chamber,
            district=district,
        )

        detail_link = item.get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return p


class Senate(LegList):
    source = URL("https://legislature.ky.gov/Legislators/senate")
    chamber = "upper"


class House(LegList):
    source = URL("https://legislature.ky.gov/Legislators/house-of-representatives")
    chamber = "lower"
