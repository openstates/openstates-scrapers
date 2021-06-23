import re
import logging

from openstates.scrape import Person, Scraper

from utils import LXMLMixin

# ----------------------------------------------------------------------------
# Logging config
logger = logging.getLogger("openstates.tx-people")


class TXPersonScraper(Scraper, LXMLMixin):
    jurisdiction = "tx"

    def _get_chamber_parties(self, chamber):
        logger.info("Getting chamber parties")
        """
        Return a dictionary that maps each district to its representative
        party for the given legislative chamber.
        """
        party_map = {"D": "Democratic", "R": "Republican"}

        chamber_map = {"upper": "S", "lower": "H"}

        parties = {}

        # use only full-session slug for this
        session = self.latest_session()[:2]

        url = (
            "https://lrl.texas.gov/legeLeaders/members/membersearch."
            "cfm?leg={}&chamber={}"
        ).format(session, chamber_map[chamber])
        page = self.lxmlize(url)

        # table is broken and doesn't have proper <tr> tags
        # so we'll group the td tags into groups of 9
        tds = self.get_nodes(
            page,
            '//div[@class="body2ndLevel"]/table//td[contains(@class, ' '"result")]',
        )

        for td_index, td in enumerate(tds):
            # 2nd and 6th column
            if td_index % 9 == 2:
                district = td.text_content().strip()
            if td_index % 9 == 6:
                party_code = td.text_content().strip()[0]
                party = party_map[party_code]
                parties[district] = party

        return parties

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
        """
        Returns a Person object representing a member of the lower
        legislative chamber.
        """
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

        return person
