# import re

from pupa.scrape import Person, Scraper
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
            '//table[@class="screenreader"]'
            '/tbody'
            '/tr'
            "/td[not(text()[contains(.,'(Deceased)')]) and not(text()[contains(.,'(Removed)')]) and not(text()[contains(.,'(Resigned)')])]"
            "/a[1]"
        ):
            member_url = "https://www.arkleg.state.ar.us" + a.get("href").replace("../", "/")

            yield from self.scrape_member(chamber, member_url)

    def scrape_member(self, chamber, member_url):
        page = self.get(member_url).text
        root = lxml.html.fromstring(page)

        name_and_party = root.xpath('string(//div[@class="col-md-12"]/h1[1])').split()

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
            img = root.xpath('//img[@class="SitePhotos MemberPhoto"]')[0]
            photo_url = "https://www.arkleg.state.ar.us" + img.attrib["src"]
        except IndexError:
            self.warning("No member photo found")
            photo_url = ""

        # Need to figure out a cleaner method for this later
        # info_box = root.xpath('string(//div[@id="bodyContent"]/div[2]/div[2])')
        try:
            district = root.xpath('string(//div[@id="bodyContent"]/div[2]/div[2]/div[3]/div[2])')
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
            phone = root.xpath('string(//div[@id="bodyContent"]/div[2]/div[2]/div[1]/div[2]/a)')
            if not phone.strip():
                raise AttributeError
        except AttributeError:
            phone = None
        try:
            email = root.xpath('string(//div[@id="bodyContent"]/div[2]/div[2]/div[2]/div[2]/a)')
            if not email.strip():
                raise AttributeError
        except AttributeError:
            email = None
        address = root.xpath('string(//div[@id="bodyContent"]/div[1]/div[1]/p/b)')

        person.add_contact_detail(type="address", value=address, note="District Office")
        if phone is not None:
            person.add_contact_detail(type="voice", value=phone, note="District Office")
        if email is not None:
            person.add_contact_detail(type="email", value=email, note="District Office")

        try:
            occupation_check = root.xpath('string(//div[@id="bodyContent"]/div[2]/div[2]/div[5]/div[1]/b)')
            if occupation_check == "Occupation:":
                person.extras["occupation"] = root.xpath('string(//div[@id="bodyContent"]/div[2]/div[2]/div[5]/div[2])')
            else:
                raise AttributeError
            if not person.extras["occupation"].strip():
                raise AttributeError
        except AttributeError:
            pass

        yield person
