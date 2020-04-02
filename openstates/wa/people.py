import re
from openstates_core.scrape import Person, Scraper
from openstates.utils import LXMLMixin


class WAPersonScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            if chamber == "upper":
                index_url = "http://www.leg.wa.gov/senate/senators/Pages/default.aspx"
            else:
                index_url = (
                    "http://www.leg.wa.gov/house/representatives/Pages/default.aspx"
                )
            yield from self.scrape_chamber(index_url, chamber)

    def scrape_chamber(self, index_url, chamber):
        doc = self.lxmlize(index_url)

        # Email addresses are listed on a separate page.
        email_list_url = "http://app.leg.wa.gov/memberemail/Default.aspx"
        email_doc = self.lxmlize(email_list_url)

        for member in doc.xpath(
            '//div[@id="allMembers"]/div[@class="memberInformation"]'
        ):
            (photo_url,) = member.xpath('.//a[text()="Print Quality Photo"]/@href')

            (title_name_party,) = member.xpath('.//span[@class="memberName"]/text()')
            (name, party) = re.search(
                r"^(?:Senator|Representative)\s(.+)\s\(([RD])\)$", title_name_party
            ).groups()
            if party == "R":
                party = "Republican"
            elif party == "D":
                party = "Democratic"

            (district_name, _district_name) = member.xpath(
                ".//a[contains(text()," ' " Legislative District")]/text()'
            )
            assert district_name == _district_name
            district_num = re.search(
                r"(\d{1,2})\w{2} Legislative District", district_name
            ).group(1)

            leg = Person(
                name=name,
                primary_org=chamber,
                image=photo_url,
                district=district_num,
                party=party,
            )

            leg.add_link(member.xpath('.//a[contains(text(), "Home Page")]/@href')[0])

            capitol_office = member.xpath(
                './/div[@class="memberColumnTitle" and'
                'text()=" Olympia Office"]/parent::div[1]/text()'
            )
            capitol_office = [l.strip() for l in capitol_office if l.strip()]

            capitol_fax = None
            capitol_phone = None
            capitol_address = None

            # Can't capture any information anyway if office data is empty,
            # so we can skip if that's the case.
            if capitol_office:
                # Retrieve capitol office fax number.
                if capitol_office[-1].startswith("Fax: "):
                    capitol_fax = capitol_office.pop().replace("Fax: ", "")

                # Retrieve capitol office phone number.
                capitol_phone = capitol_office.pop()

                # Retrieve capitol office address.
                capitol_address = "\n".join(capitol_office)

            # Retrieve the member's position from the email link.
            # We need it to find the member's email address.
            # These positions are enough to discriminate the chamber too (0 = upper, 1,2 = lower)
            email_link_url = member.xpath('.//a[contains(@href, "memberEmail")]')[
                0
            ].get("href")
            position = re.search(r"/([[0-9]+)$", email_link_url).group(1)

            # Need to get the email from the email page by matching -
            # with the member's district and position
            email = self.get_node(
                email_doc,
                './/tr/td/a[contains(@href, "memberEmail/{}/{}")]/parent::td/'
                "following-sibling::td[1]/text()".format(district_num, position),
            ).strip()

            if capitol_address:
                leg.add_contact_detail(
                    type="address", value=capitol_address, note="Capitol Office"
                )
            if email:
                leg.add_contact_detail(type="email", value=email, note="Capitol Office")
            if capitol_phone:
                leg.add_contact_detail(
                    type="voice", value=capitol_phone, note="Capitol Office"
                )
            if capitol_fax:
                leg.add_contact_detail(
                    type="fax", value=str(capitol_fax), note="Capitol Office"
                )
            _has_district_office = member.xpath(
                './/div[@class="memberColumnTitle" and' 'text()=" District Office"]'
            )
            if _has_district_office:
                # Out of both chambers, only one member has multiple district offices,
                # so ignore that. Also ignore the few members who have separate mailing addresses
                district_office = member.xpath(
                    './/div[@class="memberColumnTitle" and'
                    'text()=" District Office"]/parent::div[1]/text()'
                )
                district_office = [l.strip() for l in district_office if l.strip()]
                _end_of_first_address = district_office.index(
                    [l for l in district_office if re.search(r"\,\s*WA\s*\d{5}", l)][0]
                )
                district_address = "\n".join(
                    district_office[0 : (_end_of_first_address + 1)]
                )
                try:
                    district_phone = district_office[(_end_of_first_address + 1)]
                    assert re.match(r"\(\d{3}\) \d{3} \- \d{4}", district_phone)
                except IndexError:
                    pass
                except AssertionError:
                    pass

                if district_phone:
                    leg.add_contact_detail(
                        type="voice", value=district_phone, note="District Office"
                    )

                if district_address:
                    leg.add_contact_detail(
                        type="address", value=district_address, note="District Office"
                    )
            leg.add_source(index_url)
            leg.add_link(index_url)
            yield leg
