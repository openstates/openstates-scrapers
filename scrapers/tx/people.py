import re
import logging

from openstates.scrape import Person, Scraper

from utils import LXMLMixin

# ----------------------------------------------------------------------------
# Logging config
logger = logging.getLogger("openstates.tx-people")


class TXPersonScraper(Scraper, LXMLMixin):
    jurisdiction = "tx"

    def __init__(self, *args, **kwargs):
        super(TXPersonScraper, self).__init__(*args, **kwargs)

        self.district_re = re.compile(r"District +(\d+)")

        # Get all and only the address of a representative's office:
        self.address_re = re.compile(
            (
                # Every representative's address starts with a room number,
                # street number, or P.O. Box:
                r"(?:Room|\d+|P\.?\s*O)"
                # Just about anything can follow:
                + ".+?"
                # State and zip code (or just state) along with idiosyncratic
                # comma placement:
                + "(?:"
                + "|".join([r", +(?:TX|Texas)(?: +7\d{4})?", r"(?:TX|Texas),? +7\d{4}"])
                + ")"
            ),
            flags=re.DOTALL | re.IGNORECASE,
        )

    def _scrape_lower(self, roster_page, roster_url):
        logger.info("Scraping lower chamber roster")
        """
        Retrieves a list of members of the lower legislative chamber.
        """
        member_urls = roster_page.xpath('//a[@class="member-img"]/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(r"\d+$", url).group()))

        parties = self._get_chamber_parties("lower")

        for member_url in member_urls:
            yield from self._scrape_representative(member_url, parties)

    def _scrape_representative(self, url, parties):
        # logger.info(f'Generating representative person object from {url}')
        """
        Returns a Person object representing a member of the lower
        legislative chamber.
        """
        # url = self.get(url).text.replace('<br>', '')
        member_page = self.lxmlize(url)

        photo_url = member_page.xpath('//img[@class="member-photo"]/@src')[0]
        if photo_url.endswith("/.jpg"):
            photo_url = None

        scraped_name, district_text = member_page.xpath(
            '//div[@class="member-info"]/h2'
        )
        scraped_name = scraped_name.text_content().strip().replace("Rep. ", "")
        scraped_name = " ".join(scraped_name.split())

        name = " ".join(scraped_name.split(", ")[::-1])

        district_text = district_text.text_content().strip()
        district = str(self.district_re.search(district_text).group(1))

        # Vacant house "members" are named after their district numbers:
        if re.match(r"^District \d+$", scraped_name):
            return None

        party = parties[district]

        person = Person(name=name, district=district, party=party, primary_org="lower")

        if photo_url is not None:
            person.image = photo_url

        person.add_link(url)
        person.add_source(url)

        def office_name(element):
            """Returns the office address type."""
            return element.xpath("preceding-sibling::h4[1]/text()")[0].rstrip(":")

        offices_text = [
            {
                "name": office_name(p_tag),
                "type": office_name(p_tag).replace(" Address", "").lower(),
                "details": p_tag.text_content(),
            }
            for p_tag in member_page.xpath(
                '//h4/following-sibling::p[@class="double-space"]'
            )
        ]

        for office_text in offices_text:
            details = office_text["details"].strip()

            # A few member pages have blank office listings:
            if details == "":
                continue

            # At the time of writing, this case of multiple district
            # offices occurs exactly once, for the representative at
            # District 43:
            if details.count("Office") > 1:
                district_offices = [
                    district_office.strip()
                    for district_office in re.findall(
                        r"(\w+ Office.+?(?=\w+ Office|$))", details, flags=re.DOTALL
                    )
                ]
                offices_text += [
                    {
                        "name": re.match(r"\w+ Office", office).group(),
                        "type": "district",
                        "details": re.search(
                            r"(?<=Office).+(?=\w+ Office|$)?", office, re.DOTALL
                        ).group(),
                    }
                    for office in district_offices
                ]

            match = self.address_re.search(details)
            if match is not None:
                address = re.sub(
                    " +$",
                    "",
                    match.group().replace("\r", "").replace("\n\n", "\n"),
                    flags=re.MULTILINE,
                )
            else:
                # No valid address found in the details.
                continue

            # phone_number = extract_phone(details)
            # fax_number = extract_fax(details)

            if address:
                person.add_contact_detail(
                    type="address", value=address, note=office_text["name"]
                )
            # if phone_number:
            #     person.add_contact_detail(
            #         type="voice", value=phone_number, note=office_text["name"]
            #     )
            # if fax_number:
            #     person.add_contact_detail(
            #         type="fax", value=fax_number, note=office_text["name"]
            #     )

        yield person
