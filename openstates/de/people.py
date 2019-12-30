import re
from openstates.utils import LXMLMixin

from pupa.scrape import Person, Scraper

PARTY = {"R": "Republican", "D": "Democratic"}


class DEPersonScraper(Scraper, LXMLMixin):
    jurisdiction = "de"

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        url = {
            "upper": "https://legis.delaware.gov/json/Senate/GetSenators",
            "lower": "https://legis.delaware.gov/json/House/" + "GetRepresentatives",
        }[chamber]
        source_url = {
            "upper": "https://legis.delaware.gov/Senate",
            "lower": "https://legis.delaware.gov/House",
        }[chamber]

        data = self.post(url).json()["Data"]

        for item in data:
            if item["PersonFullName"] is None:
                # Vacant district
                self.warning(
                    "District {} was detected as vacant".format(item["DistrictNumber"])
                )
                continue

            leg_url = (
                "https://legis.delaware.gov/"
                + "LegislatorDetail?personId={}".format(item["PersonId"])
            )

            doc = self.lxmlize(leg_url)
            image_url = doc.xpath("//img/@src")[0]

            leg = Person(
                name=item["PersonFullName"],
                district=str(item["DistrictNumber"]),
                party=PARTY[item["PartyCode"]],
                primary_org=chamber,
                image=image_url,
            )
            self.scrape_contact_info(leg, doc)
            leg.add_link(leg_url, note="legislator page")
            leg.add_source(source_url, note="legislator list page")
            yield leg

    def scrape_contact_info(self, leg, doc):
        address = phone = email = None

        for label in doc.xpath("//label"):
            value = label.xpath("following-sibling::div")[0].text_content().strip()
            if label.text == "Email Address:":
                email = value
            elif label.text == "Legislative Office:":
                address = re.sub(r"\s+", " ", value).strip()
            elif label.text == "Legislative Phone:":
                phone = value

        if address:
            leg.add_contact_detail(type="address", value=address, note="Capitol Office")
        if phone:
            leg.add_contact_detail(type="voice", value=phone, note="Capitol Office")
        if email:
            leg.add_contact_detail(type="email", value=email)
