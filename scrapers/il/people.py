from openstates.scrape import Scraper, Person
import lxml.html
from utils import validate_phone_number


CHAMBER_URLS = {
    "upper": "https://ilga.gov/senate/default.asp?GA={term}",
    "lower": "https://ilga.gov/house/default.asp?GA={term}",
}

CHAMBER_ROLES = {"upper": "Senator", "lower": "Representative"}

BIRTH_DATES = {"Daniel Biss": "1977-08-27"}

AKA = {
    "Jay Hoffman": "Jay C. Hoffman",
    "Chad Hays": "Chad D Hays",
    "Randy Hultgren": "Randall M. Hultgren",
    "Scott M Bennett": "Scott M. Bennett",
    "Arthur Turner": "Arthur L. Turner",
    "Kelly Burke": "Kelly M. Burke",
    "Michael Unes": "Michael D. Unes",
    "Deb Conroy": "Deborah Conroy",
    "Charles Meier": "Charles E. Meier",
    "Bill Brady": "William E. Brady",
    "Randy Ramey, Jr.": "Harry R. Ramey, Jr.",
    "John D'Amico": "John C. D'Amico",
    "Sheri Jesiel": "Sheri L Jesiel",
    "Michael Zalewski": "Michael J. Zalewski",
    "David Reis": "David B. Reis",
    "Jason Barickman": "Jason A. Barickman",
    "Michael Tryon": "Michael W. Tryon",
    "Jehan Gordon-Booth": "Jehan A. Gordon-Booth",
    "John Cavaletto": "John D. Cavaletto",
    "Patrick J Verschoore": "Patrick J. Verschoore",
    "Patrick Verschoore": "Patrick J. Verschoore",
    "Ann Williams": "Ann M. Williams",
    "Norine Hammond": "Norine K. Hammond",
    "Nick Sauer": "Nicholas Sauer",
    "Greg Harris": "Gregory Harris",
    "Carol Sente": "Carol A. Sente",
    "David Luechtefeld": "David S. Luechtefeld",
    "Heather Steans": "Heather A. Steans",
    "Bill Cunningham": "William Cunningham",
    "Brad Halbrook": "Brad E. Halbrook",
    "Annazette Collins": "Annazette R. Collins",
    "Lawrence M. Walsh": "Lawrence M. Walsh, Jr.",
    "Lawrence Walsh, Jr.": "Lawrence M. Walsh, Jr.",
    "John Bradley": "John E. Bradley",
    "Toi W Hutchinson": "Toi W. Hutchinson",
    "Renee Kosel": "Renée Kosel",
    "La Shawn K. Ford": "LaShawn K. Ford",
    "Jerry Costello, II": "Jerry F. Costello, II",
    "Michael Connelly": "Michael G. Connelly",
    "Camille Y Lilly": "Camille Y. Lilly",
    "André Thapedi": "André M. Thapedi",
    "Careen M Gordon": "Careen M. Gordon",
    "Ron Sandack": "Ronald Sandack",
    "Ed Sullivan": "Ed Sullivan, Jr.",
    "Robert Martwick": "Robert F. Martwick",
    "Arthur J. Wilhelmi": "Arthur J. Wilhelmi",
    "Susana Mendoza": "Susan A. Mendoza",
    "Susana A Mendoza": "Susana A. Mendoza",
}


class IlPersonScraper(Scraper):
    def scrape(self, latest_only=True):
        for legislator, terms in self.legislators(latest_only).values():
            for chamber, district, start, end, party in self._join_contiguous(terms):
                role = CHAMBER_ROLES[chamber]
                legislator.add_term(
                    role,
                    chamber,
                    district=district,
                    start_date=str(start),
                    end_date=str(end),
                )

            yield legislator

    def legislators(self, latest_only):
        legs = {}

        for member, chamber, term, url in self._memberships(latest_only):
            name, _, _, district, party = member.xpath("td")
            district = district.text
            detail_url = name.xpath("a/@href")[0]

            if party.text_content().strip() == "":
                party = "Independent"
            else:
                party = {"D": "Democratic", "R": "Republican", "I": "Independent"}[
                    party.text
                ]
            name = name.text_content().strip()

            # inactive legislator, skip them for now
            if name.endswith("*"):
                name = name.strip("*")
                continue

            name = AKA.get(name, name)

            if name in legs:
                p, terms = legs[name]
                terms.append((chamber, district, term, party))
            else:
                p = Person(name, party=party)
                legs[name] = p, [(chamber, district, term, party)]

            p.add_source(url)
            p.add_source(detail_url)
            p.add_link(detail_url)

            birth_date = BIRTH_DATES.get(name, None)
            if birth_date:
                p.birth_date = birth_date

            leg_html = self.get(detail_url).text
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(detail_url)

            hotgarbage = (
                "Senate Biography Information for the 98th General "
                "Assembly is not currently available."
            )

            if hotgarbage in leg_html:
                # The legislator's bio isn't available yet.
                self.logger.warning("No legislator bio available for " + name)
                continue

            photo_url = leg_doc.xpath('//img[contains(@src, "/members/")]/@src')[0]
            p.image = photo_url

            p.contact_details = []
            # email
            email = leg_doc.xpath('//b[text()="Email: "]')
            if email:
                p.add_contact_detail(
                    type="email", value=email[0].tail.strip(), note="Capitol Office"
                )

            offices = {
                "Capitol Office": '//table[contains(string(), "Springfield Office")]',
                "District Office": '//table[contains(string(), "District Office")]',
            }

            for location, xpath in offices.items():
                table = leg_doc.xpath(xpath)
                if table:
                    for type, value in self._table_to_office(table[3]):
                        if type in ("fax", "voice") and not validate_phone_number(
                            value
                        ):
                            continue

                        p.add_contact_detail(type=type, value=value, note=location)

        return legs

    # function for turning an IL contact info table to office details
    def _table_to_office(self, table):
        addr = []
        for row in table.xpath("tr"):
            row = row.text_content().strip()
            # skip rows that aren't part of address
            if (
                not row
                or "Office:" in row
                or row == "Cook County"
                or row.startswith("Senator")
                or row == "Additional District Addresses"
                or row == ", IL"
            ):
                continue
            # fax number row ends with FAX
            elif "FAX" in row:
                yield "fax", row.replace(" FAX", "")
            # phone number starts with ( [make it more specific?]
            elif row.startswith("("):
                yield "voice", row
            # everything else is an address
            else:
                addr.append(row)

        if addr:
            yield "address", "\n".join(addr)

    def _memberships(self, latest_only):
        CURRENT_TERM = 102

        terms = [CURRENT_TERM] if latest_only else range(93, CURRENT_TERM + 1)

        for term in terms:
            for chamber, base_url in CHAMBER_URLS.items():
                url = base_url.format(term=term)

                html = self.get(url).text
                page = lxml.html.fromstring(html)
                page.make_links_absolute(url)

                for row in page.xpath("//table")[4].xpath("tr")[2:]:
                    yield row, chamber, term, url

    def _join_contiguous(self, terms):
        joined_terms = []
        terms = sorted(terms, key=lambda x: x[2])
        previous = None
        for chamber, district, term, party in terms:
            year = 1917 + term
            if not joined_terms or (chamber, district, year - 1, party) != previous:
                joined_terms.append([chamber, district, year, year, party])
            else:
                joined_terms[-1][3] = year

            previous = (chamber, district, year, party)

        return joined_terms
