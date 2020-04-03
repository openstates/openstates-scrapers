import lxml.html
from openstates.scrape import Person, Scraper


class NoDetails(Exception):
    pass


SESSION_NUMBERS = {"2011": 109, "2013": 110, "2015": 111, "2017": 112, "2019": 113}


class MTPersonScraper(Scraper):

    _roster_url = "https://leg.mt.gov/legislator-information/?session_select={}"
    _chamber_map = dict(lower="HD", upper="SD")

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber else ["upper", "lower"]

        try:
            session_num = SESSION_NUMBERS[session]
        except KeyError:
            session_num = max(SESSION_NUMBERS.values())

        self._roster_url = self._roster_url.format(session_num)
        response = self.get(self._roster_url)
        roster_table = lxml.html.fromstring(response.text).xpath(
            '//table[@id="reports-table"]/tbody'
        )[0]

        for chamber in chambers:
            yield from self._scrape_legislators(roster_table, chamber)

    def _scrape_legislators(self, roster_table, chamber):
        chamber_abbr = self._chamber_map[chamber]
        xpath = "./tr" '[./td[@class="rosterCell seatCell"]' '[contains(text(), "{}")]]'
        rows = roster_table.xpath(xpath.format(chamber_abbr))
        for row in rows:
            yield from self._scrape_legislator(row, chamber)

    def _scrape_legislator(self, row, chamber):
        name_cell = row.xpath('./td[@class="rosterCell nameCell"]/a')[0]
        name = " ".join(
            [
                line.strip()
                for line in name_cell.text_content().split("\n")
                if len(line.strip()) > 0
            ]
        )

        party_letter = row.xpath('./td[@class="rosterCell partyCell"]/text()')[
            0
        ].strip()
        party = dict(D="Democratic", R="Republican")[party_letter]

        chamber_abbr = self._chamber_map[chamber]
        district = (
            row.xpath('./td[@class="rosterCell seatCell"]' "/text()")[0]
            .replace(chamber_abbr, "")
            .strip()
        )
        try:
            email = (
                row.xpath('./td[@class="rosterCell emailCell"]' "/a/@href")[0]
                .replace("mailto:", "")
                .strip()
            )
        except IndexError:
            email = None

        phone = (
            row.xpath('./td[@class="rosterCell phoneCell"]' "/text()")[0].strip()
            or None
        )

        details_url = "https://leg.mt.gov{}".format(name_cell.attrib["href"])
        response = self.get(details_url)
        details_page = lxml.html.fromstring(response.text)

        address_lines = (
            details_page.xpath(
                '//div[@class="col-lg-6 col-md-12 text-lg-left align-self-center"]'
                '/p[contains(text(), "Address")]'
            )[0]
            .text_content()
            .replace("Address", "")
            .split("\n")
        )
        address = "\n".join(
            [line.strip() for line in address_lines if len(line.strip()) > 0]
        )

        legislator = Person(
            name=name, district=district, party=party, primary_org=chamber
        )

        legislator.add_contact_detail(
            type="address", value=address, note="Capitol Office"
        )
        if phone is not None:
            legislator.add_contact_detail(
                type="voice", value=phone, note="Capitol Office"
            )

        if email is not None:
            legislator.add_contact_detail(type="email", value=email, note="E-mail")

        legislator.add_link(details_url)
        legislator.add_source(self._roster_url)

        yield legislator
