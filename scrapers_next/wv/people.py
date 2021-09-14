from spatula import URL, CSS, HtmlListPage, XPath
from openstates.models import ScrapePerson
import re


class LegList(HtmlListPage):
    selector = XPath("//*[@id='wrapper']/table/tr[@valign='top']")

    def process_item(self, item):
        name = CSS("td a").match(item)[1].text_content().strip()
        if name == "Vacant":
            self.skip()

        party = CSS("td").match(item)[1].text_content().strip()
        if party == "Democrat":
            party = "Democratic"

        district = CSS("td").match(item)[2].text_content().strip()
        if re.search(r"0\d", district):
            district = re.sub("0", "", district)

        p = ScrapePerson(
            name=name,
            state="wv",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        p.add_source(self.source.url)

        email = CSS("td").match(item)[4].text_content().strip()
        p.email = email

        capp_addr_txt = XPath("td[4]/text()").match(item)
        capp_addr = ""
        for line in capp_addr_txt:
            capp_addr += line.strip()
            capp_addr += " "
        p.capitol_office.address = capp_addr.strip()

        phone = CSS("td").match(item)[5].text_content().strip()
        p.capitol_office.voice = phone

        detail_link = CSS("td a").match(item)[1].get("href")
        detail_link = detail_link.replace(" ", "%20")
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return p


class Senate(LegList):
    source = URL("http://www.wvlegislature.gov/Senate1/roster.cfm")
    chamber = "upper"


class House(LegList):
    source = URL("http://www.wvlegislature.gov/House/roster.cfm")
    chamber = "lower"
