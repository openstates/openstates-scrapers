from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        all_info = CSS("ul.list-group li").match(self.root)

        county = CSS("span").match_one(all_info[1]).text_content().strip()
        p.extras["counties represented"] = county

        service = CSS("span").match_one(all_info[2]).text_content().strip()
        if service != "":
            p.extras["service"] = service

        occupation = CSS("span").match_one(all_info[3]).text_content().strip()
        if occupation != "":
            p.extras["occupation"] = occupation

        address = XPath(".//span/text()").match(all_info[4])
        if len(address) > 1:
            district_addr = address[0] + " " + address[1]
            p.district_office.address = district_addr
        elif address[0].strip() != ",":
            district_addr = address[0].strip()
            p.district_office.address = district_addr
        # storing 'Address' as district_office.address

        capitol_phone = CSS("span").match_one(all_info[5]).text_content().strip()
        if capitol_phone != "(505)":
            p.capitol_office.voice = capitol_phone

        # capitol_room = CSS("span").match(all_info[6]).text_content().strip()

        office_phone = CSS("span").match_one(all_info[7]).text_content().strip()
        if office_phone != "":
            p.district_office.voice = office_phone

        home_phone = CSS("span").match_one(all_info[8]).text_content().strip()
        if home_phone != "":
            p.extras["home phone"] = home_phone

        email = CSS("a").match_one(all_info[9]).text_content().strip()
        p.email = email

        return p


class LegList(HtmlListPage):
    selector = CSS("div.col-xs-6.col-sm-3.col-md-2.col-lg-2")

    def process_item(self, item):
        name_party = CSS("span").match(item)[0].text_content().strip().split(" - ")
        name = name_party[0].strip()
        party = name_party[1].strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"
        elif party == "(DTS)":
            party = "Independent"

        district = CSS("span").match(item)[1].text_content().strip()
        district = re.search(r"District:\s(.+)", district).groups()[0].strip()

        p = ScrapePerson(
            name=name,
            state="nm",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        img = CSS("img").match_one(item).get("src")
        p.image = img

        return LegDetail(p, source=detail_link)


class Senate(LegList):
    source = URL("https://www.nmlegis.gov/Members/Legislator_List?T=S")
    chamber = "upper"


class House(LegList):
    source = URL("https://www.nmlegis.gov/Members/Legislator_List?T=R")
    chamber = "lower"
