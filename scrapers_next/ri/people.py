from spatula import HtmlListPage, CSS, XPath
from ..common.people import ScrapePerson


class LegList(HtmlListPage):
    def process_item(self, item):
        name = (
            CSS("td")
            .match(item)[1]
            .text_content()
            .strip()
            .lstrip(r"[Senator\s|Rep.\s]")
        )
        district = CSS("td").match(item)[0].text_content()
        email = CSS("td").match(item)[2].text_content()

        p = ScrapePerson(
            name=name,
            state="ri",
            party="Democratic",
            district=district,
            chamber=self.chamber,
        )

        bio = CSS("td center a").match_one(item).get("href")

        p.email = email
        p.add_link(bio)
        p.add_source(self.source.url, note="Contact Web Page")
        p.add_source(self.url, note="Detail Excel Source")

        return p


class AssemblyList(LegList):
    source = "http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=75)
    chamber = "lower"
    url = "http://www.rilegislature.gov/SiteAssets/MailingLists/Representatives.xls"


class SenList(LegList):
    source = "http://webserver.rilegislature.gov/Email/SenEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=38)
    chamber = "upper"
    url = "http://www.rilegislature.gov/SiteAssets/MailingLists/Senators.xls"
