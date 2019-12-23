import re

import lxml.html
from pupa.scrape import Scraper, Person


PARTY_DICT = {"D": "Democratic", "R": "Republican", "I": "Independent"}


class WIPersonScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.jurisdiction.legislative_sessions[-1]
            self.info("no session specified, using %s", session["identifier"])

        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session["identifier"])

    def scrape_chamber(self, chamber, session):
        url = "https://docs.legis.wisconsin.gov/{}/legislators/{}".format(
            session, {"upper": "senate", "lower": "assembly"}[chamber]
        )

        body = self.get(url).text
        page = lxml.html.fromstring(body)
        page.make_links_absolute(url)

        for row in page.xpath(
            ".//div[@class='box-content']/div[starts-with(@id,'district')]"
        ):
            if row.xpath(".//a/@href") and not row.xpath(".//a[text()='Vacant']"):
                rep_url = row.xpath(".//a[text()='Details']/@href")[0].strip("https://")
                rep_url = "https://" + rep_url
                rep_doc = lxml.html.fromstring(self.get(rep_url).text)
                rep_doc.make_links_absolute(rep_url)

                full_name = (
                    rep_doc.xpath('.//div[@id="district"]/h1/text()')[0]
                    .replace("Senator ", "")
                    .replace("Representative ", "")
                )

                party = rep_doc.xpath('.//div[@id="district"]//small/text()')
                if len(party) > 0:
                    party = PARTY_DICT[party[0].split("-")[0].strip("(").strip()]
                else:
                    party = None
                district = rep_doc.xpath('.//div[@id="district"]/h3/a/@href')[1]
                district = district.split("/")[-1]
                district = str(int(district))

                # email
                email = rep_doc.xpath("//span[@class='info email']/a/text()")
                if email:
                    email = email[0]
                else:
                    email = ""

                assert party is not None, "{} is missing party".format(full_name)

                person = Person(
                    name=full_name, district=district, primary_org=chamber, party=party
                )

                img = rep_doc.xpath('.//div[@id="district"]/img/@src')
                if img:
                    person.image = img[0]

                # office ####
                address_lines = rep_doc.xpath('.//span[@class="info office"]/text()')
                address = "\n".join(
                    [line.strip() for line in address_lines if line.strip() != ""]
                )
                person.add_contact_detail(
                    type="address", value=address, note="Capitol Office"
                )

                phone = rep_doc.xpath('.//span[@class="info telephone"]/text()')
                if phone:
                    phone = re.sub(r"\s+", " ", phone[1]).strip()
                    person.add_contact_detail(
                        type="voice", value=phone, note="Capitol Office"
                    )

                fax = rep_doc.xpath('.//span[@class="info fax"]/text()')
                if fax:
                    fax = re.sub(r"\s+", " ", fax[1]).strip()
                    person.add_contact_detail(
                        type="fax", value=fax, note="Capitol Office"
                    )

                if email:
                    person.add_contact_detail(
                        type="email", value=email, note="Capitol Office"
                    )

                person.add_link(rep_url)
                person.add_source(rep_url)

                yield person
