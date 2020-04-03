import lxml.html

from openstates_core.scrape import Person, Scraper, Organization


class SCPersonScraper(Scraper):
    def __init__(self, *args, **kwargs):
        """  CSS isn't there without this, it serves up a mobile version. """
        super().__init__(*args, **kwargs)
        self.user_agent = "Mozilla/5.0"

    def scrape(self, chamber=None):
        """ Generator Function to pull in (scrape) data about person from state website."""

        chambers = [chamber] if chamber else ["upper", "lower"]
        for c in chambers:
            yield from self.scrape_chamber(c)

    def scrape_chamber(self, chamber):
        if chamber == "lower":
            url = "http://www.scstatehouse.gov/member.php?chamber=H"
        else:
            url = "http://www.scstatehouse.gov/member.php?chamber=S"

        seen_committees = {}

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[@class="membername"]'):
            full_name = a.text
            leg_url = a.get("href")

            if full_name.startswith("Senator"):
                full_name = full_name.replace("Senator ", "")
            if full_name.startswith("Representative"):
                full_name = full_name.replace("Representative ", "")

            leg_html = self.get(leg_url).text
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(leg_url)

            if "Resigned effective" in leg_html:
                self.info("Resigned")
                continue

            party, district, _ = leg_doc.xpath(
                '//p[@style="font-size: 17px;' ' margin: 0 0 0 0; padding: 0;"]/text()'
            )

            if "Republican" in party:
                party = "Republican"
            elif "Democrat" in party:
                party = "Democratic"

            # District # - County - Map
            district = district.split()[1]
            try:
                photo_url = leg_doc.xpath('//img[contains(@src,"/members/")]/@src')[0]
            except IndexError:
                self.warning("No Photo URL for {}".format(full_name))
                photo_url = ""
            person = Person(
                name=full_name,
                district=district,
                party=party,
                primary_org=chamber,
                image=photo_url,
            )

            # office address / phone
            try:
                addr_div = leg_doc.xpath(
                    '//div[@style="float: left; width: 225px;'
                    ' margin: 10px 5px 0 20px; padding: 0;"]'
                )[0]
                capitol_address = addr_div.xpath(
                    'p[@style="font-size: 13px;' ' margin: 0 0 10px 0; padding: 0;"]'
                )[0].text_content()

                phone = addr_div.xpath(
                    'p[@style="font-size: 13px;'
                    ' margin: 0 0 0 0; padding: 0;"]/text()'
                )[0]
                capitol_phone = phone.strip()

                if capitol_address:
                    person.add_contact_detail(
                        type="address", value=capitol_address, note="Capitol Office"
                    )

                if capitol_phone:
                    person.add_contact_detail(
                        type="voice", value=capitol_phone, note="Capitol Office"
                    )
            except IndexError:
                self.warning("no capitol address for {0}".format(full_name))

            # home address / phone
            try:
                addr_div = leg_doc.xpath(
                    '//div[@style="float: left;'
                    ' width: 225px; margin: 10px 0 0 20px;"]'
                )[0]
                addr = addr_div.xpath(
                    'p[@style="font-size: 13px;' ' margin: 0 0 10px 0; padding: 0;"]'
                )[0].text_content()

                phone = addr_div.xpath(
                    'p[@style="font-size: 13px;'
                    ' margin: 0 0 0 0; padding: 0;"]/text()'
                )[0]
                phone = phone.strip()
                if addr:
                    person.add_contact_detail(
                        type="address", value=addr, note="District Office"
                    )

                if phone:
                    person.add_contact_detail(
                        type="voice", value=phone, note="District Office"
                    )
            except IndexError:
                self.warning("no district address for {0}".format(full_name))

            person.add_link(leg_url)
            person.add_source(url)
            person.add_source(leg_url)

            # committees (skip first link)
            for com in leg_doc.xpath('//a[contains(@href, "committee.php")]')[1:]:
                if com.text.endswith(", "):
                    committee, role = com.text_content().rsplit(", ", 1)

                    # known roles
                    role = {
                        "Treas.": "treasurer",
                        "Secy.": "secretary",
                        "Secy./Treas.": "secretary/treasurer",
                        "V.C.": "vice-chair",
                        "1st V.C.": "first vice-chair",
                        "Co 1st V.C.": "co-first vice-chair",
                        "2nd V.C.": "second vice-chair",
                        "3rd V.C.": "third vice-chair",
                        "Ex.Officio Member": "ex-officio member",
                        "Chairman": "chairman",
                    }[role]
                else:
                    committee = com.text
                    role = "member"

                # only yield each committee once
                if committee not in seen_committees:
                    com = Organization(
                        name=committee, classification="committee", chamber=chamber
                    )
                    com.add_source(url)
                    seen_committees[committee] = com
                    yield com
                else:
                    com = seen_committees[committee]

                person.add_membership(com, role=role)

            yield person
