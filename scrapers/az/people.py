from openstates.scrape import Person, Scraper
from lxml import html
import re


class AZPersonScraper(Scraper):
    jurisdiction = "az"
    parties = {
        "R": "Republican",
        "D": "Democratic",
        "L": "Libertarian",
        "I": "Independent",
        "G": "Green",
    }

    def get_party(self, abbr):
        return self.parties[abbr]

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

        # TODO: old AZ scraper allowed old sessions, they seem to be gone?
        # self.validate_term(term, latest_only=True)

    def scrape_chamber(self, chamber):
        body = {"lower": "H", "upper": "S"}[chamber]
        url = "http://www.azleg.gov/MemberRoster/?body=" + body
        page = self.get(url).text

        # there is a bad comment closing tag on this page
        page = page.replace("--!>", "-->")

        root = html.fromstring(page)

        path = "//table//tr"
        roster = root.xpath(path)[1:]
        for row in roster:
            position = ""
            name, district, party, email, room, phone, = row.xpath("td")

            if email.attrib.get("class") == "vacantmember":
                continue  # Skip any vacant members.

            link = name.xpath("string(a/@href)")
            if len(name) == 1:
                name = name.text_content().strip()
            else:
                position = name.tail.strip()
                name = name[0].text_content().strip()
            if "--" in name:
                name = name.split("--")[0].strip()

            linkpage = self.get(link).text
            linkpage = linkpage.replace("--!>", "-->")
            linkroot = html.fromstring(linkpage)
            linkroot.make_links_absolute(link)

            photos = linkroot.xpath("//img[contains(@src, 'MemberPhoto')]")

            if len(photos) != 1:
                self.warning("no photo on " + link)
                photo_url = ""
            else:
                photo_url = photos[0].attrib["src"]

            district = district.text_content().strip()
            party = party.text_content().strip()
            email = email.text_content().strip()

            if email.startswith("Email: "):
                email = email.replace("Email: ", "").lower() + "@azleg.gov"
            else:
                email = ""

            party = self.get_party(party)
            room = room.text_content().strip()
            if chamber == "lower":
                address = "House of Representatives\n"
            else:
                address = "Senate\n"
            address = (
                address + "1700 West Washington\n Room " + room + "\nPhoenix, AZ 85007"
            )

            phone = phone.text_content().strip()
            if "602" not in re.findall(r"(\d+)", phone):
                phone = "602-" + phone

            leg = Person(
                primary_org=chamber,
                image=photo_url,
                name=name,
                district=district,
                party=party,
            )
            leg.add_contact_detail(type="address", value=address, note="Capitol Office")
            leg.add_contact_detail(type="voice", value=phone, note="Capitol Office")
            leg.add_party(party=party)
            leg.add_link(link)

            if email:
                leg.add_contact_detail(type="email", value=email)
            if position:
                leg.add_membership(name_or_org=party, role=position)
                # leg.add_role(position, term, chamber=chamber,
                #             district=district, party=party)

            leg.add_source(url)

            # Probably just get this from the committee scraper
            # self.scrape_member_page(link, session, chamber, leg)
            yield leg

    """
    def scrape_member_page(self, url, session, chamber, leg):
        html = self.get(url).text
        root = html.fromstring(html)
        # get the committee membership
        c = root.xpath('//td/div/strong[contains(text(), "Committee")]')
        for row in c.xpath('ancestor::table[1]')[1:]:
            name = row[0].text_content().strip()
            role = row[1].text_content().strip()
            leg.add_membership(role=role, name_or_org=name)

        leg.add_source(url)
    """
