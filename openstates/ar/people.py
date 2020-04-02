import re

from openstates_core.scrape import Person, Scraper
import lxml.html

from .common import get_slug_for_session


class ARLegislatorScraper(Scraper):
    _remove_special_case = True
    latest_only = True

    def scrape(self, chamber=None, session=None):

        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        session_slug = get_slug_for_session(session)
        session_year = int(session[:4])
        odd_year = session_year if session_year % 2 else session_year - 1
        url = (
            "http://www.arkleg.state.ar.us/assembly/%s/%s/Pages/"
            "LegislatorSearchResults.aspx?member=&committee=All&chamber="
        ) % (odd_year, session_slug)
        page = self.get(url).text
        root = lxml.html.fromstring(page)

        for a in root.xpath(
            '//table[@class="dxgvTable"]'
            '/tr[contains(@class, "dxgvDataRow")]'
            "/td[1]/a"
        ):
            member_url = a.get("href").replace("../", "/")

            yield from self.scrape_member(chamber, member_url)

    def scrape_member(self, chamber, member_url):
        page = self.get(member_url).text
        root = lxml.html.fromstring(page)

        name_and_party = root.xpath('string(//td[@class="SiteNames"])').split()

        title = name_and_party[0]
        # Account for Representative-Elect and Senator-Elect, for incoming class
        if title.startswith("Representative"):
            chamber = "lower"
        elif title.startswith("Senator"):
            chamber = "upper"

        full_name = " ".join(name_and_party[1:-1])

        party = name_and_party[-1]

        if party == "(R)":
            party = "Republican"
        elif party == "(D)":
            party = "Democratic"
        elif party == "(G)":
            party = "Green"
        elif party == "(I)":
            party = "Independent"
        elif "-Elect" in title and not party.startswith("("):
            self.warning("Member-elect is currently missing a party")
            full_name = " ".join(name_and_party[1:])
            party = ""
        else:
            raise AssertionError("Unknown party ({0}) for {1}".format(party, full_name))

        try:
            img = root.xpath('//img[@class="SitePhotos"]')[0]
            photo_url = img.attrib["src"]
        except IndexError:
            self.warning("No member photo found")
            photo_url = ""

        # Need to figure out a cleaner method for this later
        info_box = root.xpath('string(//table[@class="InfoTable"])')
        try:
            district = re.search(r"District(.+)\r", info_box).group(1)
        except AttributeError:
            self.warning("Member has no district listed; skipping them")
            return

        person = Person(
            name=full_name,
            district=district,
            party=party,
            primary_org=chamber,
            image=photo_url,
        )

        person.add_link(member_url)
        person.add_source(member_url)

        try:
            phone = re.search(r"Phone(.+)\r", info_box).group(1)
        except AttributeError:
            phone = None
        try:
            email = re.search(r"Email(.+)\r", info_box).group(1)
        except AttributeError:
            email = None
        address = root.xpath("//nobr/text()")[0].replace(u"\xa0", " ")

        person.add_contact_detail(type="address", value=address, note="District Office")
        if phone is not None:
            person.add_contact_detail(type="voice", value=phone, note="District Office")
        if email is not None:
            person.add_contact_detail(type="email", value=email, note="District Office")

        try:
            person.extras["occupation"] = re.search(
                r"Occupation(.+)\r", info_box
            ).group(1)
        except AttributeError:
            pass

        yield person
