import re

from openstates.scrape import Person, Scraper
from utils import LXMLMixin

import xlrd

excel_mapping = {
    "district": 0,
    "town_represented": 1,
    "full_name": 2,
    "party": 3,
    "address": 4,
    "email": 5,
}

translate = {
    "Democrat": "Democratic",
    "Republican": "Republican",
    "Independent": "Independent",
}

link_col_ix = 4


class RIPersonScraper(Scraper, LXMLMixin):
    jurisdiction = "ri"
    latest_only = True

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber(chamber="upper")
            yield from self.scrape_chamber(chamber="lower")

    def scrape_chamber(self, chamber=None):
        if chamber == "upper":
            url = "http://webserver.rilin.state.ri.us/Documents/Senators.xls"
            rep_type = "Senator"
            contact_url = (
                "http://webserver.rilin.state.ri.us/Email/SenEmailListDistrict.asp"
            )
        elif chamber == "lower":
            url = "http://webserver.rilin.state.ri.us/Documents/Representatives.xls"
            rep_type = "Representative"
            contact_url = (
                "http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp"
            )

        contact_page = self.lxmlize(contact_url)
        contact_info_by_district = {}
        for row in contact_page.xpath('//tr[@valign="TOP"]'):
            tds = row.xpath("td")
            (detail_link,) = tds[link_col_ix].xpath(".//a/@href")
            # Ignore name (2nd col). We have a regex built up below for the spreadsheet name
            # I don't want to touch
            district, _, email, phone = [
                td.text_content().strip() for td in tds[:link_col_ix]
            ]
            contact_info_by_district[district] = {
                "email": email,
                "phone": phone,
                "detail_link": detail_link,
            }

        self.urlretrieve(url, "ri_leg.xls")

        wb = xlrd.open_workbook("ri_leg.xls")
        sh = wb.sheet_by_index(0)

        for rownum in range(1, sh.nrows):
            d = {
                field: sh.cell(rownum, col_num).value
                for field, col_num in excel_mapping.items()
            }

            # Convert float to an int, and then to string, the required format
            district = str(int(d["district"]))
            if d["full_name"].upper() == "VACANT":
                self.warning("District {}'s seat is vacant".format(district))
                continue

            contact_info = contact_info_by_district[district]

            # RI is very fond of First M. Last name formats and
            # they're being misparsed upstream, so fix here
            (first, middle, last) = ("", "", "")
            full_name = re.sub(
                r"^{}(?=\s?[A-Z].*$)".format(rep_type), "", d["full_name"]
            ).strip()
            if re.match(r"^\S+\s[A-Z]\.\s\S+$", full_name):
                (first, middle, last) = full_name.split()

            # Note - if we ever need to speed this up, it looks like photo_url can be mapped
            # from the detail_link a la /senators/Paolino/ -> /senators/pictures/Paolino.jpg
            detail_page = self.lxmlize(contact_info["detail_link"])
            (photo_url,) = detail_page.xpath('//div[@class="ms-WPBody"]//img/@src')

            person = Person(
                primary_org=chamber,
                district=district,
                name=full_name,
                party=translate[d["party"]],
                image=photo_url,
            )
            person.extras["town_represented"] = d["town_represented"]
            person.extras["name_first"] = first
            person.extras["name_middle"] = middle
            person.extras["name_last"] = last
            person.add_link(detail_link)

            if d["address"]:
                person.add_contact_detail(
                    type="address", value=d["address"], note="District Office"
                )
            if contact_info["phone"]:
                person.add_contact_detail(
                    type="voice", value=contact_info["phone"], note="District Office"
                )
            if contact_info["email"]:
                person.add_contact_detail(
                    type="email", value=contact_info["email"], note="District Office"
                )

            person.add_source(contact_url)
            person.add_source(contact_info["detail_link"])

            yield person
