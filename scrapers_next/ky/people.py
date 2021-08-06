from spatula import CSS, HtmlListPage, URL, HtmlPage, SelectorError, XPath
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

        counties = CSS("div .center ul li").match_one(self.root).text_content()
        if re.search(r"\(Part\)", counties):
            counties = re.search(r"(.+)\s\(Part\)", counties).groups()[0]
        counties = counties.split(", ")
        p.extras["counties represented"] = counties

        email = (
            XPath("//div[2]/p[contains(text(), 'Email')]")
            .match_one(self.root)
            .getnext()
            .text_content()
        )
        p.email = email

        addresses = CSS("address").match(self.root)
        for addr in addresses:
            address_clean = " "
            addr_type = addr.getprevious().text_content()
            addr_lst = XPath("text()").match(addr)
            address_clean = address_clean.join(addr_lst)
            if addr_type == "Mailing Address":
                p.extras["mailing address"] = address_clean
            elif addr_type == "Legislative Address":
                p.district_office.address = address_clean
            elif addr_type == "Capitol Address":
                p.capitol_office.address = address_clean

        phones = (
            XPath("//div[2]/p[contains(text(), 'Phone Number(s)')]")
            .match_one(self.root)
            .getnext()
        )
        phones = XPath("text()").match(phones)
        for num in phones:
            kind, num = num.split(": ")
            if kind == "LRC" and num.endswith(" (fax)"):
                fax = num.replace(" (fax)", "")
                p.capitol_office.fax = fax
            elif kind == "LRC":
                p.capitol_office.voice = num
            elif kind == "Home" and num.endswith(" (fax)"):
                fax = num.replace(" (fax)", "")
                p.district_office.fax = fax
            elif kind == "Home":
                p.district_office.voice = num
            elif kind == "Work" and num.endswith(" (fax)"):
                fax = num.replace(" (fax)", "")
                p.extras["fax"] = fax
            elif kind == "Work":
                p.extras["voice"] = num

        try:
            twitter = (
                XPath("//div[2]/p[contains(text(), 'Twitter')]")
                .match_one(self.root)
                .getnext()
                .text_content()
                .lstrip("@")
            )
            p.ids.twitter = twitter
        except SelectorError:
            twitter = None

        try:
            home_city = (
                XPath("//div[2]/p[contains(text(), 'Home City')]")
                .match_one(self.root)
                .getnext()
                .text_content()
            )
            p.extras["home city"] = home_city
        except SelectorError:
            home_city = None

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

        return LegDetail(p, source=detail_link)


class Senate(LegList):
    source = URL("https://legislature.ky.gov/Legislators/senate")
    chamber = "upper"


class House(LegList):
    source = URL("https://legislature.ky.gov/Legislators/house-of-representatives")
    chamber = "lower"
